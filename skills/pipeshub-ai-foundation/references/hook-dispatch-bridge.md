<!-- capsule-v2 -->
# Hook dispatch bridge — how does exception-based Agent.run() keep its shape while decisions move into the kernel Pipeline?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter migrating a legacy hook chain onto a decision-based middleware kernel must know which events re-raise as exceptions (and WHICH exception), which are pure transforms, and how cancellation stays distinguishable from blocking.

## dispatch_* family — one bridge module
**Path/Symbol:** `agent/hook_dispatch.py:dispatch_pre_agent` (64-70), `dispatch_post_agent` (73-77), `dispatch_pre_turn` (80-90), `dispatch_post_turn` (93-99), `dispatch_pre_model` (102-116), `dispatch_post_model` (119-132), `dispatch_guardrail_input/output` (135-150), `call_model_wrapped` (153-157).
**Signature:** each takes `(kernel, payload..., *, scope=None)`; transforms return mutated payloads (`dispatch_pre_model -> list[Message]`, `dispatch_post_model -> ModelResponseContext`); guards raise or return None.
**Data Shape:** Every dispatcher builds a typed context carrying the scope + `session_id = scope.run.session_id if scope else None` — session_id used to be filled only for tool contexts by ToolExecutor; this module back-fills it everywhere.

### Decisive source
```python
# hook_dispatch.py — cancellation is a DENY + metadata flag, raised as a DIFFERENT exception
async def dispatch_pre_turn(kernel, turn_index, *, scope=None):
    ctx = TurnContext(turn_index=turn_index, scope=scope,
                      session_id=scope.run.session_id if scope else None)
    await kernel.on(HookEvent.PRE_TURN).dispatch(ctx)
    if ctx.decision == PreDecision.DENY:
        if ctx.metadata.get("cancelled"):
            raise RunCancelled(ctx.decision_reason or "Cancelled")
        raise HookBlocked(ctx.decision_reason or f"blocked before turn {turn_index}")
```

**Flow:** build context → dispatch through the ONE Pipeline (`kernel.on(event)`) → translate outcome: PRE_AGENT/PRE_TURN deny ⇒ raise `HookBlocked`; guardrail BLOCK ⇒ raise `HookBlocked`; POST_AGENT/POST_TURN/POST_MODEL ⇒ return (post-events can't veto retroactively); PRE_MODEL ⇒ pure message-list transform; PRE_MODEL_CALL ⇒ `kernel.wrapper(...).compose(call_llm)` nested closure because retry must RE-INVOKE the chain N times.
**Invariant:** The bridge exists so every call site in agent/__init__.py keeps the EXACT pre-kernel shape — control flow wasn't restructured (the LLM-call/guardrail asyncio.wait race stayed untouched). Only PRE_TURN distinguishes cancellation: `metadata["cancelled"]=True` on an otherwise ordinary deny upgrades the raise from HookBlocked to RunCancelled. A porter who collapses both to HookBlocked breaks `Agent.run()`'s cancelled status/event reporting (caught at agent/__init__.py:588 → status="cancelled", EventType.CANCELLATION instead of blocked).
**Probe:** no dedicated test file for `agent/hook_dispatch.py` itself (coverage caveat). Deterministic checks: graph trace shows inbound callers `Agent.step` (hop 1) + ReActLoop/SingleShotLoop/ReflexionLoop/IncrementalLoop/PhaseDriver/OrchestratorLoop `.run` (hop 2) — 29 callers total; producer contract pinned by turn_guards.py:49-67 (`check_not_cancelled` sets `ctx.metadata["cancelled"]=True` before denying) and consumer by core/exceptions.py RunCancelled docstring.

---

## ContextWindow seam (context package companion)
**Path/Symbol:** `context/base.py:ContextWindow` ABC (11-39) with async-by-design rationale docstring; `ContextBudget.for_model` / `effective_max_tokens` (62-81); implementations `manager.py:ContextManager` (full history) and `window.py:SlidingWindowContext._evict` (19-30).
**Signature:** `add/messages/token_count/clear` ALL async; `for_model(model, reserved_output_tokens=8000, reserved_artifact_tokens=0)`; `effective_max_tokens = max(max_tokens - reserved_artifact_tokens, 1_000)`.
**Data Shape:** Budget derived from the model's real context window minus output headroom (never a flat number); artifact reserve carve-out shrinkable when result_schema proxies replace full data.

### Decisive source
```python
# window.py — eviction skips SYSTEM messages and terminates when only they remain
while await self.token_count() > self._max_tokens:
    evicted = False
    for i, msg in enumerate(self._messages):
        if msg.role != MessageRole.SYSTEM:
            self._messages.pop(i); evicted = True; break
    if not evicted:
        break                                   # system-only ⇒ cannot evict further
# clear() keeps SYSTEM messages; manager.py's ContextManager never evicts (external summarization trims)
```

**Flow:** add() appends then evicts oldest non-SYSTEM until under budget → messages() returns a COPY → clear() preserves system prompt. Full-history vs sliding variants are interchangeable behind the ABC.
**Invariant:** Every method is async NOT because current implementations do I/O but because a future durable store-backed history must slot in without a breaking signature change — Agent already awaits every other collaborator mid-turn; a sync context method would be the one inconsistent exception. System messages are immortal under eviction. Two eviction strategies, one interface: pick per deployment, never fork the call sites.
**Probe:** no dedicated unit test file for context/base.py or window.py (coverage caveat). Deterministic checks: ContextBudget consumed by `dispatch_pre_model` signature (hook_dispatch.py:102-116) and shapers (test_context_compaction.py / test_tool_result_clearing.py import from agent_loop_lib.context.base).
**Coverage caveat:** behavior grounded in source + consumers; direct-test probe absent for these two files.
