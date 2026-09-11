<!-- capsule-v2 -->
# Turn-guard installers — how do deterministic per-turn guards get wired without double-firing across a shared kernel?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** Several Agent objects share one runtime's kernel — how are always-on guards installed exactly once while behavior-changing gates stay opt-in?

## Marker-attribute idempotency + the always-on vs opt-in split
**Path/Symbol:** `backend/python/app/agent_loop_lib/hooks/middleware/builtin/turn_guards.py:install_turn_guards/install_supervisor_confidence_gate/install_stall_detection` (L90–161); marker consts L44–46.
**Signature:** `install_turn_guards(kernel, *, budget=None, cancellation_token=None) -> None`; installers match `Callable[[HookRegistry], None]` (the shape `AgentSpec.middleware` expects).

```python
_INSTALLED_MARKER = "_agent_turn_guards_installed"

def install_turn_guards(kernel, *, budget=None, cancellation_token=None) -> None:
    if getattr(kernel, _INSTALLED_MARKER, False):
        return
    setattr(kernel, _INSTALLED_MARKER, True)
    if budget is not None:
        kernel.on(HookEvent.PRE_TURN).use(require_budget(budget))
    if cancellation_token is not None:
        kernel.on(HookEvent.PRE_TURN).use(check_not_cancelled(cancellation_token))
    kernel.on(HookEvent.PRE_MODEL).use(warn_before_deadline())
    kernel.on(HookEvent.POST_MODEL).use(default_truncation_recovery())
```

**Data Shape:** Always-on set (every role needs them): budget gate (PRE_TURN), cancellation deny (PRE_TURN; also sets `ctx.metadata["cancelled"]=True` so dispatch raises distinct `RunCancelled` not generic `HookBlocked`), deadline nudge (PRE_MODEL appends a UserMessage when `max_turns - turn_index == 2`), truncation recovery (POST_MODEL populates `recovery_message`/`recovery_tool_results`). Opt-in set (model-visible behavior changes): supervisor confidence gate (POST_TOOL_USE blocks LOW-confidence create_plan results) and stall detection (POST_TURN + PRE_MODEL pair with warn/fail thresholds).

### Decisive source
```python
# turn_guards.py docstring (L14-21): "It is idempotent per kernel instance
# ... because every Agent sharing one AgentRuntime shares that runtime's
# single kernel by reference ..., so several Agent objects can legitimately
# wrap the very same kernel — installing twice would double-register
# warn_before_deadline, firing the deadline warning message twice into
# context instead of once."
#
# and (L26-33): supervisor_gate/stall_detection "deliberately NOT part of it:
# both change model-visible behavior ..., so a role that never calls
# create_plan or that legitimately needs many low-signal turns ... shouldn't
# have them running unconditionally on every turn."
```

**Flow:** `Agent.__init__` calls `install_turn_guards(kernel)` → marker set on first call, later Agents sharing the kernel no-op → ControlPlane adds opt-in gates only for roles whose config lists them (`cfg.hooks`) → stall-detection caveat: first spec to install wins its thresholds for ALL agents on that shared kernel (separate AgentRuntime required for different thresholds).

**Invariant:** idempotency keys off the KERNEL, not the Agent — per-Agent memoization would double-fire the deadline warning into shared context. The always-on/opt-in boundary is behavioral, not stylistic: anything that injects messages or blocks tool results must stay opt-in or short-lived sub-agents inherit costs they never asked for.
**Probe:** `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_turn_guards.py:66/:74` (opt-in gates NOT installed by default), `:90` (blocks once opted in), `:97/:118` (both installers idempotent), `:105` (stall detection warns once installed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "install_turn_guards warn_before_deadline check_not_cancelled", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt marker-based per-kernel idempotency and the deterministic-guards-vs-behavior-changing-gates taxonomy. Adapt the marker attribute names, warning copy, and the two-turns-left constant to host. Omit PipesHub's specific guard thresholds where your budget/cancellation model differs. Direct tests read at HEAD (test_turn_guards.py, pytest asyncio_mode=auto).
