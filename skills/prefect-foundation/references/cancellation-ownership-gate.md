<!-- capsule-v2 -->

# Cancellation ownership gate — Which side of a process boundary is allowed to write Cancelling/Cancelled state?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** When both a runner and an in-process engine could observe the same cancellation, how does the child avoid duplicating state history and hooks?

## One env switch + one in-process flag, OR-ed

**Path/Symbol:** `src/prefect/flow_engine.py:BaseFlowRunEngine._engine_owns_cancellation_handling (586-604)`; consumed by `handle_cancellation` (sync `901-920`, async shielded `1603-1618`) and by `call_hooks` (`1019-1045`).

**Signature:** `_engine_owns_cancellation_handling() -> bool` = `self._started_with_in_process_parent_flow_run_context or os.environ.get("PREFECT__ENABLE_CANCELLATION_AND_CRASHED_HOOKS", "true").lower() == "true"`.

**Data Shape:** `_started_with_in_process_parent_flow_run_context` is latched once inside `initialize_run` from `FlowRunContext.get() is not None and not parent_flow_run_context.detached`. The runner sets the env var to `"false"` ONLY for subprocesses it supervises. Engine-reported Crashed states are NOT governed by this switch — they stay engine-owned unconditionally.

### Decisive source
```python
def _engine_owns_cancellation_handling(self) -> bool:
    """Return whether this engine owns cancellation state and hooks.

    Runner-managed subprocesses set
    `PREFECT__ENABLE_CANCELLATION_AND_CRASHED_HOOKS=false`
    and retain ownership of acknowledged cancellation state and hooks.
    ... Same-process nested subflows have no external supervisor, so the
    engine ignores suppression when it started inside a non-detached parent
    `FlowRunContext`.
    """
```

**Flow:** cancellation observed → ownership check → owned: `set_state(Cancelling(msg), force=True)` then `set_state(Cancelled(msg), force=True)` → not owned: skip BOTH writes entirely but STILL record `_raised`, telemetry exception, end span on failure ("Flow run was cancelled."). Hook selection mirrors the same predicate: `on_cancellation_hooks` run only when engine-owned; `on_crashed` hooks always run.

**Invariant:** (1) Default is OWNED (`"true"`): top-level flows with no runner keep writing their own terminal states — the suppression must be opt-in per subprocess. (2) The async variant wraps everything in `CancelScope(shield=True)` so the state writes survive the very cancellation being reported; porting without the shield loses the Cancelled transition under asyncio cancellation. (3) Skipping the writes never skips telemetry/hook bookkeeping — `_raised` is set either way so the caller's result path still raises.

**Probe:** `grep -c 'PREFECT__ENABLE_CANCELLATION_AND_CRASHED_HOOKS' src/prefect/flow_engine.py` → 3 (ownership check + subprocess-env injection + comment). Direct tests: `tests/test_flow_engine.py:470 test_runner_managed_subprocesses_skip_child_owned_cancellation_state_writes` (env false → set_state NOT called, `_raised is exc`) vs `:489 test_top_level_non_runner_flows_force_cancellation_state_writes` and `:508 test_same_process_subflows_force_cancellation_state_writes` (both → exactly 2 calls, first is_cancelling, second is_cancelled).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "_engine_owns_cancellation_handling", "limit": 3}'
```

## Verdict
Adopt the two-signal ownership predicate whenever child processes and a supervisor can both see the same event (prevents duplicate state history); adapt the env-var name and latch timing to your harness; omit Prefect's specific hook roster.
