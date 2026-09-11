<!-- capsule-v2 -->
# Executor-event requeue ladder — which stale executor events must NOT kill a task?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** When the executor reports SUCCESS but the DB shows the TI still queued/scheduled, when is that an external kill and when is it a benign race?

## `ti_queued and not ti_requeued` gate before failing externally-killed TIs
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:process_executor_events` (1359–1705).
**Signature:** classmethod `process_executor_events(cls, executor, job_id, scheduler_dag_bag, session, eagerly_load_dag_tags=False) -> int`.
**Data Shape:** Consumes `executor.get_event_buffer()` dict keyed by `TaskInstanceKey | ConnectionTestKey | CallbackKey`. Try-number map built first: multiple events for one primary key with differing try_numbers log a warning and the LAST wins.

### Decisive source
```python
ti_requeued = (
    ti.queued_by_job_id != job_id  # Another scheduler has queued this task again
    or executor.has_task(ti)       # This scheduler has this task already
    or (
        # Resume-after-defer: trigger moved TI to scheduled or queued (next_method set)
        # before we saw the executor success from the defer exit for the same try_number.
        ti.state in (TaskInstanceState.SCHEDULED, TaskInstanceState.QUEUED)
        and state == TaskInstanceState.SUCCESS
        and ti.next_method is not None
    )
)
if ti_queued and not ti_requeued:
    ... stats.incr("scheduler.tasks.killed_externally", ...)
```

**Flow:** only FAILED/SUCCESS/QUEUED/RUNNING/RESTARTING states enter processing → row-lock TI set (`skip_locked`) → QUEUED/RUNNING events just record `external_executor_id` and continue → terminal-looking event against unfinished state runs the ladder above → if genuinely killed: log "state mismatch", send `TaskCallbackRequest` (only when task has callbacks), handle cleared-while-running (`RESTARTING + SUCCESS` ⇒ reset for retry with raised `max_tries`), send EmailRequest, finally `ti.handle_failure()`.
**Invariant:** The defer-resume race (#66374/#67287) MUST pass through without side effects: a trigger moved the TI forward before this scheduler drained the worker's post-defer exit success; failing it here would kill a healthy resumed task. Callback-type decision (`UP_FOR_RETRY` vs `FAILED`) must use the SAME `is_eligible_to_retry()` predicate that `handle_failure` will apply, or callback and state diverge.
**Probe:** `grep -c 'next_method is not None' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 1; direct tests `test_process_executor_events_stale_success_when_scheduled_after_defer` (:909) and `..._queued_after_defer` (:970) assert zero `killed_externally` metric while `next_method` is set.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "process_executor_events killed_externally requeued defer next_method", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the requeue-escape ladder shape (ownership check / still-tracked check / logical-resume check). Adapt which states count as resume evidence to your own defer mechanism. Omit the multi-team metric tags and email plumbing.
