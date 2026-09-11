<!-- capsule-v2 -->
# Cancel-before-start registry — how do you cancel a run that has not started yet, without losing the intent?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What must a cancellation registry guarantee for background runs whose cancel request can arrive before registration?

## InMemoryRunCancellationManager
**Path/Symbol:** `libs/agno/agno/run/cancellation_management/in_memory_cancellation_manager.py:12` (facade `libs/agno/agno/run/cancel.py` with module-global `_cancellation_manager` :11 and `_member_drain_tasks: Dict[str, Set[asyncio.Task]]` :16).
**Signature:** `register_run(run_id) / cancel_run(run_id) -> bool (was_registered) / is_cancelled(run_id) / raise_if_cancelled(run_id) / cleanup_run(run_id)` + member-cascade trio (`register_member_run(team_run_id, member_run_id)`, `get_member_run_ids`, `cleanup_member_runs`) + drain bucket (`register_member_drain_task`, `adrain_member_tasks(team_run_id, timeout=5.0)`).
**Data Shape:** `_cancelled_runs: Dict[str, bool]` guarded by BOTH a `threading.Lock` (sync API) and an `asyncio.Lock` (async API); member map `Dict[team_run_id, Set[member_run_id]]`; swap in a Redis impl via `set_cancellation_manager()`.

### Decisive source
```python
def register_run(self, run_id: str) -> None:
    """Uses setdefault to preserve any existing cancellation intent
    (cancel-before-start support for background runs)."""
    with self._lock:
        self._cancelled_runs.setdefault(run_id, False)

def cancel_run(self, run_id: str) -> bool:
    """Always stores cancellation intent, even for runs not yet registered."""
    was_registered = run_id in self._cancelled_runs
    self._cancelled_runs[run_id] = True
    return was_registered

async def adrain_member_tasks(team_run_id: str, timeout: float = 5.0) -> None:  # run/cancel.py:151
    tasks = {t for t in _member_drain_tasks.get(team_run_id, set()) if not t.done()}
    if not tasks: return
    try:
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Timed out draining {len(tasks)} member task(s) for run {team_run_id}")
```

**Flow:** cancel may land at any time → `cancel_run` writes `True` unconditionally (returns whether it was registered) → when the run later starts, `register_run` uses **setdefault** so the pre-existing `True` survives → every checkpoint calls `raise_if_cancelled` → terminal path (`finally`) calls `cleanup_run`. Member delegation registers each member run under the team's id; the team cancel handler drains its delegate-task bucket (bounded 5s) BEFORE persisting so each member's post-cancel `add_member_run` lands on the response.
**Invariant:** (1) `register_run` must NEVER blind-write `False` — that erases a pre-start cancel and the zombie run completes un-cancelled. (2) Drain is best-effort bounded: timeout logs and continues rather than blocking persistence forever. (3) The drain-bucket self-cleans via `add_done_callback(_discard)` so a run never leaks an empty set if cleanup is never reached. (4) Sync and async APIs guard with SEPARATE locks by design.
**Probe:** live-executed at pin: cancel-before-register returns False ✓, setdefault preserves intent through register+raise ✓, cleanup removes entry ✓, member-map cleanup ✓; integration matrix `tests/integration/teams/test_team_run_cancellation.py` (incl. `test_cancel_non_existent_team_run`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "InMemoryRunCancellationManager cancel_run setdefault", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the setdefault-vs-blind-write distinction verbatim — it is the whole bug class; adapt storage to your infra (agno ships a Redis twin implementing the same base); omit the module-global swap mechanism. Direct tests executed green.
