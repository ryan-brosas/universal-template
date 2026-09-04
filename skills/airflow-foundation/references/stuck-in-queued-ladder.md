<!-- capsule-v2 -->
# Stuck-in-queued ladder — revoke, retry twice via Log-table counting, then fail

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How does the scheduler recover tasks the broker/executor lost while QUEUED, without infinitely churning them?

## Attempt counter read from the Log table AFTER the last "running" event
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:_handle_tasks_stuck_in_queued` (3111–3134), `_get_num_times_stuck_in_queued` (3246–3286), `_maybe_requeue_stuck_ti` (3146–3227), `_reschedule_stuck_task` (3229–3243).
**Signature:** sweep interval `scheduler.task_queued_timeout_check_interval`; stuck predicate: `state=QUEUED ∧ queued_dttm < now-task_queued_timeout ∧ queued_by_job_id == self.job.id`.
**Data Shape:** Retry budget `_num_stuck_queued_retries` (default 2, undocumented config `num_stuck_in_queued_retries`). Log events: `"stuck in queued reschedule"` / `"stuck in queued tries exceeded"`.

### Decisive source
```python
if last_running_time is not None:
    statement = statement.where(Log.dttm > last_running_time)
...
if num_times_stuck < self._num_stuck_queued_retries:
    session.add(Log(event=TASK_STUCK_IN_QUEUED_RESCHEDULE_EVENT, ...))
    self._reschedule_stuck_task(ti, session=session)   # state=SCHEDULED, queued_dttm=None, queued_by_job_id=None
else:
    ... # fail path
finally:
    ti.set_state(TaskInstanceState.FAILED, session=session)
    executor.fail(ti.key)
```

**Flow:** per executor bucket: `executor.revoke_task(ti)` first (tell the executor to drop it if it actually has it), count prior stuck-reschedules scoped to THIS try (only entries after the most recent "running" log — sensors re-enter running repeatedly with one try_number, so unscoped counts would exhaust after three polls across ALL tries), requeue under budget else fail-with-callback. Failure path resolves bundle/version info server-side so on_failure_callback executes against pinned code; callback fires BEFORE the finally sets FAILED.
**Invariant:** The Log table is durable attempt-state that survives scheduler restarts — counting in a column would need its own migration and cleanup; scoping by last-running-time makes sensors get N attempts PER TRY not per lifetime. Only the OWNING scheduler (`queued_by_job_id == me`) sweeps its own stuck tasks, avoiding cross-scheduler tug-of-war.
**Probe:** `grep -c 'TASK_STUCK_IN_QUEUED_RESCHEDULE_EVENT' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 3; direct test `test_handle_stuck_queued_tasks_multiple_attempts` at `airflow-core/tests/unit/jobs/test_scheduler_job.py:3855`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "handle_tasks_stuck_in_queued revoke requeue Log TASK_STUCK", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt log-as-counter recovery ladders with ownership-scoped sweeps. Adapt where you persist attempt counters. Omit bundle-pinning resolution if you don't pin code versions per run.
