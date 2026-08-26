<!-- capsule-v2 -->
# Orphan adoption — how do a dead scheduler's in-flight tasks survive failover?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** When a scheduler crashes, which of its QUEUED/RUNNING tasks are adopted by peers vs reset for rescheduling?

## Liveness UPDATE → row-locked scan → per-executor try_adopt → reset remainder
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:adopt_or_reset_orphaned_tasks` (3379–3486); states `State.adoptable_states = {QUEUED, RUNNING, RESTARTING}`.
**Signature:** `adopt_or_reset_orphaned_tasks(self, *, session) -> int` (count of resets).
**Data Shape:** Dead-job detection: bulk `UPDATE Job SET state=FAILED WHERE job_type='SchedulerJob' AND state=RUNNING AND latest_heartbeat < now - scheduler_health_check_threshold`. Candidate join: TI.state IN adoptable ∧ queued_by Job NOT RUNNING ∧ DagRun RUNNING.

### Decisive source
```python
tis_to_adopt_or_reset_query = with_row_locks(query, of=TI, session=session, skip_locked=True)
...
for executor, tis in exec_to_tis.items():
    to_reset.extend(executor.try_adopt_task_instances(tis))
for ti in to_reset:
    # ... Record the current try to TaskInstanceHistory first ...
    ti.prepare_db_for_next_try(session=session)
    ti.state = None
    ti.queued_by_job_id = None
    ti.external_executor_id = None
    ti.clear_next_method_args()
for ti in set(tis_to_adopt_or_reset) - set(to_reset):
    ti.queued_by_job_id = self.job.id   # re-parent adopted TIs to ME
```

**Flow:** runs once at startup then every `orphaned_tasks_check_interval` (300s) inside `run_with_db_retries`; executors decide adoption (Celery can re-attach by external id; local executors cannot ⇒ reset). Resets: history snapshot FIRST (audit of abandoned attempt), then state=None, clear ownership + external id + deferral args — the TI re-enters scheduling from scratch and may burn a new try. Adopted TIs get their `queued_by_job_id` re-pointed at the adopting job so the NEXT orphan sweep attributes them correctly; Airflow-2-era rows get defensive fixes (`last_heartbeat_at`/conf None).
**Invariant:** History-before-reset is mandatory or the abandoned attempt vanishes from the audit trail; only the executor knows whether its work is externally addressable (adoptable), so the scheduler must defer that decision rather than guess.
**Probe:** `grep -c 'try_adopt_task_instances' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 1; direct test `test_adopt_or_reset_orphaned_tasks_stale_scheduler_jobs` at `airflow-core/tests/unit/jobs/test_scheduler_job.py:5467`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "adopt_or_reset_orphaned_tasks try_adopt reset prepare_db_for_next_try", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt heartbeat-liveness + adopt-or-reset with history-first bookkeeping. Adapt what your executor's try_adopt can actually reattach to. Omit legacy Airflow-2 backfill shims.
