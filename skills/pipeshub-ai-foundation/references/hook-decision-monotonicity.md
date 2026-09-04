<!-- capsule-v2 -->
# Monotonic hook decisions — why can't a later middleware override an earlier deny?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How must context objects expose decisions so a permissive middleware registered after a strict one can never silently weaken the decision?

## Escalate-only decision API — no public setter
**Path/Symbol:** `backend/python/app/agent_loop_lib/hooks/middleware/context.py:ToolCallContext.deny/ask/_escalate` (L102–116); `backend/python/app/agent_loop_lib/hooks/middleware/decisions.py:PRE_SEVERITY/POST_SEVERITY` (L41–50).
**Signature:** `def deny(self, reason) -> None` / `def ask(self, reason) -> None`, both delegating to `_escalate(new, reason)`; `_decision: PreDecision = PreDecision.ALLOW` is private.

```python
# decisions.py — higher number = more severe / more restrictive
PRE_SEVERITY: dict[PreDecision, int]  = {ALLOW: 0, ASK: 1, DENY: 2}
POST_SEVERITY: dict[PostDecision, int] = {CONTINUE: 0, BLOCK: 1}

# context.py — the ONLY mutation path for _decision
def _escalate(self, new: PreDecision, reason: str) -> None:
    if PRE_SEVERITY[new] > PRE_SEVERITY[self._decision]:
        self._decision = new
        self.decision_reason = reason
```

**Data Shape:** Gate contexts (`ToolCallContext`, `AgentLifecycleContext`, `TurnContext`, `GuardrailContext`) carry `_decision` + `decision_reason` and expose only escalate methods (`ask()` is a documented no-op when already DENY). Observe contexts (`ToolResultContext`) expose `block()` over `{CONTINUE:0, BLOCK:1}`. Reducer contexts (`ModelCallContext`, `ModelResponseContext`) have **no decision at all** — shaping never blocks. `GuardrailContext.block()` short-circuits via PostDecision.BLOCK.

### Decisive source
```python
# ToolCallContext docstring contract (context.py L4-9): "Middleware never
# assigns a decision directly (there is no public setter for ``decision``);
# it calls ctx.deny(reason)/ctx.ask(reason)/ctx.block(reason). These
# escalate-only methods enforce the severity ordering ... so a decision can
# only get *more* restrictive as it passes through the stack, never less."
```

**Flow:** every middleware starts from ALLOW → each may call `ctx.ask(...)` or `ctx.deny(...)` → `_escalate` applies the change only if strictly more severe → pipeline's `is_terminal` predicate reads the final value → executor branches on DENY/ASK/ALLOW.

**Invariant:** monotonicity is structural, not conventional — there is no code path that lowers a decision once raised; the strict `>` comparison also makes duplicate `deny()` calls idempotent while keeping the FIRST escalation's reason only when severity ties are lost... note precisely: on equal severity the original reason survives (`>` not `>=`). A porter adding a "soft-deny" third enum value MUST insert it into the severity map or comparisons silently misorder.
**Probe:** `tests/unit/agents/adapter/test_sandbox_bridge.py` imports `PreDecision/PostDecision` and drives deny/block through real contexts; `tests/unit/agent_loop_lib/tools/test_executor_ask_decision.py:63` (`ctx.ask(reason)` path observed by the executor's `_on_ask` handler); `test_require_critique.py:95/:292` (deny persists across middleware).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "PreDecision POST_SEVERITY escalate deny ask", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the private-field + escalate-only-methods pattern and the two severity maps verbatim — this is fully portable to any host with gate/observe hooks. Adapt enum names to host vocabulary. Omit nothing here; the reducer-without-decision split (PRE_MODEL has no deny) is equally load-bearing. Coverage caveat: no dedicated test file asserts severity ordering in isolation; ordering is exercised indirectly through dispatch tests above.
