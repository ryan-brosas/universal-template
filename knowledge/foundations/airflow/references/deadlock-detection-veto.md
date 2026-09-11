<!-- capsule-v2 -->
# Deadlock detection — when does a run with unfinished tasks get FAILED instead of RUNNING?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How does the scheduler distinguish "waiting on upstream" from "nothing can ever run" and fail only the latter?

## `unfinished.should_schedule and not are_runnable_tasks` ⇒ all_tasks_deadlocked
**Path/Symbol:** `airflow-core/src/airflow/models/dagrun.py:DagRun.update_state` (1267–1410); `_are_premature_tis` (1740–1757).
**Signature:** `update_state(self, *, session, execute_callbacks=True) -> tuple[list[TI], DagCallbackRequest | None]`.
**Data Shape:** `should_schedule` is a NEGATIVE gate: True only when NO unfinished TI has `depends_on_past`, `max_active_tis_per_dag`, or `max_active_tis_per_dagrun`, and none is DEFERRED/AWAITING_INPUT. Otherwise the deadlock check is skipped entirely.

### Decisive source
```python
elif unfinished.should_schedule and not are_runnable_tasks:
    self.log.error("Task deadlock (no runnable tasks); marking run %s failed", self)
    self.set_state(DagRunState.FAILED)
    self.notify_dagrun_state_changed(msg="all_tasks_deadlocked")
```
with `are_runnable_tasks = schedulable_tis or changed_tis or (self._are_premature_tis(...)[0] if ...)` — premature TIs are upstream-blocked tasks that still have runnable ancestors, so they are NOT deadlocked.

**Flow:** compute scheduling decisions → if unfinished and should_schedule: probe whether anything is runnable now or changed this pass → terminal branches in order: all-finished+any-failed ⇒ FAILED; all-finished+all-success/skipped ⇒ SUCCESS (+ prune DAGRUN-scoped deadlines); should_schedule-but-nothing-runnable ⇒ FAILED "all_tasks_deadlocked" (blocking TI = first unfinished task downstream of a finished one, used as callback context) → else stay RUNNING.
**Invariant:** Only tasks whose waiting condition CANNOT be lifted by scheduling participate: parked states (DEFERRED/AWAITING_INPUT) and history-coupled flags (depends_on_past, per-DAG concurrency caps) veto deadlock detection because their resolution lives outside this tick. Failing a run whose tasks are merely deferred would kill healthy async work.
**Probe:** `grep -c 'msg="all_tasks_deadlocked"' airflow-core/src/airflow/models/dagrun.py` → 1 (plus 2 occurrences of the reason string overall); direct tests `test_dagrun_deadlock` (:379) AND its complement `test_dagrun_no_deadlock_with_restarting` (:401) in `airflow-core/tests/unit/models/test_dagrun.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "dagrun update_state deadlock should_schedule premature", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt negative-gated deadlock detection with explicit parked-state vetoes. Adapt which states count as parked for your engine. Omit deadline pruning and listener notification plumbing.
