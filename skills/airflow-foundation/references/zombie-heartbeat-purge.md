<!-- capsule-v2 -->
# Zombie purge — lock, revalidate, then fail heartbeat-lost RUNNING tasks

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How does the scheduler kill workers that stopped heartbeating WITHOUT clobbering a terminal state the worker may have just committed?

## FOR UPDATE scan → per-TI `refresh_from_db` revalidation → handle_failure + executor change_state
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:_find_and_purge_task_instances_without_heartbeats` (3616–3638), `_find_task_instances_without_heartbeats` (3640–3671), `_purge_task_instances_without_heartbeats` (3673–3815).
**Signature:** interval `task_instance_heartbeat_timeout_detection_interval` (10s); timeout `task_instance_heartbeat_timeout`; predicate: `state IN (RUNNING, RESTARTING) ∧ last_heartbeat_at < now - timeout ∧ queued_by_job_id == self.job.id`.
**Data Shape:** Callback type decided by `ti.is_eligible_to_retry()` — UP_FOR_RETRY vs FAILED — using the SAME predicate `fetch_handle_failure_context` applies ("this previously diverged for RESTARTING task instances with max_tries=0").

### Decisive source
```python
# The scan locked this row (FOR UPDATE / skip_locked), but revalidate against the
# committed state before emitting any side effect: a worker can commit a terminal state
# (e.g. SUCCESS) around the same time the scan runs. ...
ti.refresh_from_db(session=session)
if ti.state not in (TaskInstanceState.RUNNING, TaskInstanceState.RESTARTING):
    ... continue
...
ti.handle_failure(error=msg, session=session)
executor.change_state(ti.key, TaskInstanceState.FAILED, remove_running=True)
```

**Flow:** find (row-locked, skip_locked for HA) → purge per TI: refresh+revalidate state → build timeout message → load serialized task (fail_fast/email context; failure to load still fails the TI, minus context) → send TaskCallbackRequest → optional EmailRequest (sent HERE directly because after handle_failure moves the TI out of RUNNING, process_executor_events' own email path becomes unreachable) → handle_failure → executor.change_state(remove_running=True) so slot accounting frees immediately.
**Invariant:** Lock-then-recheck is defense in depth against the worker's commit racing the scheduler's transaction; skipping revalidation emits spurious failure callbacks for successful tasks. Zombie detection is scoped to TIs this scheduler queued (`queued_by_job_id == self.job.id`) so HA peers never double-purge.
**Probe:** `grep -c 'heartbeat timeout' airflow-core/src/airflow/jobs/scheduler_job_runner.py` ≥ 2 (Log event + log text); direct test `test_find_and_purge_task_instances_without_heartbeats` at `airflow-core/tests/unit/jobs/test_scheduler_job.py:8375`, plus regression `test_purge_without_heartbeat_skips_when_missing_dag_version` (:3772).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "find purge task instances without heartbeats zombie refresh revalidate", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lock-revalidate-fail with single-source callback typing and immediate executor slot release. Adapt heartbeat storage to your worker registry. Omit email-request plumbing if notifications flow elsewhere.
