<!-- capsule-v2 -->
# Worker-side concurrency requeue — why can a RUNNING task be silently reset to None?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** What happens when concurrency limits are hit AFTER a worker picked up the task (race between queueing and execution)?

## Two-tier dependency check inside `_check_and_change_state_before_execution`
**Path/Symbol:** `airflow-core/src/airflow/models/taskinstance.py:_check_and_change_state_before_execution` (1353–1490).
**Signature:** `_check_and_change_state_before_execution(cls, task_instance, verbose=True, ..., pool=None, external_executor_id=None, *, session) -> bool`.
**Data Shape:** First pass `RUNNING_DEPS - REQUEUEABLE_DEPS`: non-runnable ⇒ return False (task stays put). Second pass `REQUEUEABLE_DEPS` (concurrency/pool limits): unmet ⇒ `ti.state = None` and return False.

### Decisive source
```python
if not ti.are_dependencies_met(dep_context=dep_context, session=session, verbose=True):
    ti.state = None
    cls.logger().warning(
        "Rescheduling due to concurrency limits reached "
        "at task runtime. Attempt %s of %s. State set to NONE.",
        ti.try_number,
        ti.max_tries + 1,
    )
    ti.queued_dttm = timezone.utcnow()
    session.merge(ti)
    session.commit()
    return False
```

**Flow:** worker claims QUEUED TI → refresh with `lock_for_update` → hard deps unmet ⇒ leave untouched → soft (requeueable) deps unmet ⇒ reset to None (scheduler will re-pick it later; NOT counted as a failure/try) → set RUNNING, `end_date=None`, log "running", commit, dispose pooled engine connections to avoid "max number of connections reached" on fork-heavy workers. Resume-after-defer keeps the ORIGINAL `start_date` (`ti.start_date if ti.next_method else now`), and UP_FOR_RESCHEDULE restores the first TaskReschedule start date.
**Invariant:** A None-reset is deliberately NOT a failure: try_number stays, no on-failure callbacks fire, the TI simply returns to the scheduler pool. Porters who map this branch onto their failure path inflate retry counts and fire spurious callbacks.
**Probe:** `grep -c 'Rescheduling due to concurrency limits reached' airflow-core/src/airflow/models/taskinstance.py` → 1; direct test `test_requeue_over_dag_concurrency` at `airflow-core/tests/unit/models/test_taskinstance.py:310`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "check_and_change_state_before_execution requeueable deps concurrency none state", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier dep check with silent-requeue semantics for capacity races discovered at claim time. Adapt which deps are "hard" vs "requeueable". Omit the engine-dispose hack if your runtime doesn't fork per task.
