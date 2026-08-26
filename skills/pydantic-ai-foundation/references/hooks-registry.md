<!-- capsule-v2 -->
# Hooks registry — decorator-registered callbacks and the three dispatch shapes

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How do you expose framework hooks as plain decorated functions without losing middleware chaining, timeouts, or per-tool scoping?

## Hooks capability
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/capabilities/hooks.py:Hooks` (:718-1273), `_make_wrap_link` (:1279-1302), `_call_entry` (:240-253), `handle_deferred_tool_calls` accumulation (:1254-1273).
**Signature:** Registry `dict[str, list[_HookEntry]]`; entries carry `func, timeout, tools?`; `@hooks.on.before_tool_execute(tools=['dangerous'], timeout=5.0)` (bare OR parameterized); constructor kwargs mirror every hook name.
**Data Shape:** One capability instance holds N hook functions per lifecycle key; tool-scoped entries filter by `call.tool_name ∈ frozenset(tools)` at dispatch time (`_filter_tool_entries`).

### Decisive source
```python
# hooks.py:887-894 — wrap_* builds a REAL middleware chain in REVERSE registration order
async def wrap_run(self, ctx, *, handler):
    entries = self._get('wrap_run')
    if not entries:
        return await handler()
    chain: Callable[..., Any] = handler
    for entry in reversed(entries):
        chain = _make_wrap_link(entry, 'wrap_run', ctx, {}, chain, None)
    return await chain()

# hooks.py:1254-1273 — deferred handlers ACCUMULATE across capabilities; each sees only
# what earlier handlers left unresolved; all-None → behave as if no handler existed
accumulated = DeferredToolResults()
remaining = requests
any_handled = False
for entry in self._get('handle_deferred_tool_calls'):
    result = await _call_entry(entry, 'handle_deferred_tool_calls', ctx, requests=remaining)
    if result is None or not (result.approvals or result.calls):
        continue
    any_handled = True
    accumulated.update(result)
    remaining_or_none = remaining.remaining(result)
    if remaining_or_none is None:
        break
    remaining = remaining_or_none
return accumulated if any_handled else None
```

**Flow:** Registration appends to per-key lists preserving user order → dispatch takes one of THREE shapes: (1) piping hooks (before/after/prepare/after_run) run sequentially, each receiving the previous return value; (2) wrap hooks fold into a middleware chain built by iterating REVERSED entries so first-registered wraps outermost; (3) error hooks try each entry in order, REPLACING `error` with whatever the entry raised — if none recovered, the last error propagates. Timeouts wrap each call in `anyio.fail_after` → `HookTimeoutError(hook_name, func_name, timeout)` (subclass of BOTH AgentRunError and TimeoutError). Sync functions auto-await via `inspect.isawaitable`. Event streams: `_on_event` callbacks sit INNERMOST (per-event), explicit stream wrappers chain outside them, and ALL wrapped generators are closed in reverse on exit.
**Invariant:** Wrap order inversion is the classic porter trap: registration order == outermost-first, so the CHAIN must be assembled over `reversed(entries)`. The accumulation protocol must break early when a handler fully resolves (`remaining() → None`) and must return None when NOTHING was resolved so downstream "no handler" behavior (e.g. envelope-as-output) still applies.
**Probe:** `tests/test_capabilities.py::test_multiple_hooks_same_event` (:12210), `::TestWrapRun::test_wrap_run` (:12271), `::test_timeout` (:12315), `::test_deferred_tool_handler_accumulation` (:22576 — two capabilities resolving different calls), `::test_deferred_tool_handler_via_hooks_constructor_kwarg_and_accumulation` (:24002).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "Hooks registry make_wrap_link filter_tool_entries HookTimeoutError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the registry + three-dispatch-shape design (pipe/wrap/error-ladder) with timeout enforcement and accumulating deferred handlers; adapt decorator naming to your API; omit event-stream plumbing if you have no streaming events. Caveat: source read at HEAD this session.
