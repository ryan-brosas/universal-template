<!-- capsule-v2 -->
# HookRegistry kernel — how do lifecycle events compose middleware without a fixed hook chain?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** When replacing a fixed `Hook` ABC chain with composable middleware, which composition primitive backs which event, and what does each event's error policy have to be?

## One Pipeline (or Wrapper) per event, built fresh per registry
**Path/Symbol:** `backend/python/app/agent_loop_lib/hooks/registry.py:_PIPELINE_FACTORIES` (L34–61), `HookRegistry.__init__` (L67–72).
**Signature:** `_PIPELINE_FACTORIES: dict[HookEvent, Callable[[], Pipeline]]`; `HookRegistry.on(event) -> Pipeline`, `.wrapper(event) -> Wrapper`, `.register_event(name, pipeline)`.

```python
_PIPELINE_FACTORIES: dict[HookEvent, Callable[[], Pipeline]] = {
    HookEvent.PRE_TOOL_USE: lambda: Pipeline(
        is_terminal=lambda ctx: ctx.decision == PreDecision.DENY, fail_closed=True),
    HookEvent.POST_TOOL_USE: lambda: Pipeline(
        is_terminal=lambda ctx: ctx.decision == PostDecision.BLOCK, fail_closed=False),
    ...
    # Pure reducer: every shaper runs, in registration order, mutating
    # ctx.messages in place
    HookEvent.PRE_MODEL: lambda: Pipeline(is_terminal=lambda ctx: False, fail_closed=False),
}
_WRAPPER_EVENTS: frozenset[HookEvent] = frozenset({HookEvent.PRE_MODEL_CALL})
```

**Data Shape:** 11 builtin `HookEvent`s (`hooks/events.py`): gate/observe events (PRE_TOOL_USE, POST_TOOL_USE, PRE_AGENT/POST_AGENT, PRE_TURN/POST_TURN, GUARDRAIL_INPUT/_OUTPUT) + reducer events (PRE_MODEL, POST_MODEL) are Pipeline-backed; PRE_MODEL_CALL alone is Wrapper-backed. Each event pairs with exactly one context type (`hooks/middleware/context.py` module table). Nothing process-global — every `ControlPlane` builds its own instance so tests/concurrent runs never share middleware state.

### Decisive source
```python
# pipeline.py dispatch — terminal stop lives INSIDE next_fn, not in the walker
async def next_fn() -> None:
    nonlocal idx
    if self._is_terminal(ctx):
        return  # hard stop: a terminal decision was already reached
    idx += 1
    if idx >= len(matched):
        return
    try:
        await matched[idx](ctx, next_fn)
    except Exception as exc:
        self._handle_middleware_error(ctx, exc)
        if not self._is_terminal(ctx):
            await next_fn()
```

**Flow:** middleware registers via `kernel.on(event).use(mw)` or `.use(pattern, mw)` → at dispatch time the stack is filtered to matchers firing for ctx → `next()` walks them one at a time mutating ctx in place → once `is_terminal(ctx)` is true `next()` refuses to advance → on middleware exception: recorded into `ctx.metadata["middleware_errors"]`, then either `ctx.deny(...)` (fail_closed gates) or continue (fail_open observers).

**Invariant:** (1) A terminal decision can never be "un-decided" — the check sits inside `next_fn` itself, so even a middleware that never calls `next()` cannot bypass it and later middleware can't run after DENY regardless of registration order. (2) Error policy is per-event, not per-middleware: pre-execution gates fail CLOSED (a broken permission check denies), post-execution reducers fail OPEN (a broken formatter must not destroy a valid tool result). Porters who flip these swap a security bug for a reliability bug. (3) PRE_MODEL_CALL must be a Wrapper because retry needs to re-invoke "the rest of the chain" N times — a single-pass `next()` continuation consumes the step forever.
**Probe:** `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_require_critique.py:107` (`test_pending_critique_short_circuits_later_middleware` — dispatch through a real `kernel.on(PRE_TOOL_USE)` stops after deny); `:292` (blocked state persists across a second dispatch); `tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py:248` (retry hook wires through ControlPlane).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "HookRegistry on wrapper register_event", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-primitive-per-event table (gate→fail-closed Pipeline, observer/reducer→fail-open Pipeline, retry-style wrap→Wrapper) and the fresh-per-owner registry. Adapt event names/context types to host vocabulary; adapt glob/tag matcher routing to host path scheme. Omit the PipesHub-specific builtin middleware set (wire those from your own config). Coverage caveat: no dedicated unit test file for pipeline.py/wrapper.py themselves — behavior is pinned transitively via test_require_critique/test_turn_guards/test_executor_ask_decision driving real kernels.
