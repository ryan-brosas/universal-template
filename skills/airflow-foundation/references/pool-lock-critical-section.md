<!-- capsule-v2 -->
# Pool-row lock critical section — how is task enqueueing made single-writer under HA?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** Which locks make "pick TIs by priority and queue them" safe against concurrent schedulers, and what happens when the lock is busy?

## Advisory lock (Postgres) + `SELECT ... FROM pool FOR UPDATE NOWAIT`
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:_executable_task_instances_to_queued` (657–706, 838, 2073–2081); `_critical_section_enqueue_task_instances` (1201–1250).
**Signature:** `_executable_task_instances_to_queued(self, max_tis: int, session) -> list[TI]`.
**Data Shape:** On PostgreSQL a transactional advisory lock (`pg_try_advisory_xact_lock(DBLocks.SCHEDULER_CRITICAL_SECTION.value)`) is tried first; failure raises a synthetic `OperationalError("Failed to acquire advisory lock", orig=RuntimeError("55P03"))` so both dialects share one failure path. Pool rows locked `nowait=True` via `Pool.slots_stats(lock_rows=True)`. Caller catches `OperationalError`, checks `is_lock_not_available_error`, increments `scheduler.critical_section_busy`, rolls back and returns 0.

### Decisive source
```python
lock_acquired = session.execute(
    text("SELECT pg_try_advisory_xact_lock(:id)").bindparams(
        id=DBLocks.SCHEDULER_CRITICAL_SECTION.value
    )
).scalar()
if not lock_acquired:
    raise OperationalError("Failed to acquire advisory lock", params=None, orig=RuntimeError("55P03"))
# Get the pool settings. ... Throws an exception if lock cannot be obtained, rather than blocking
pools = Pool.slots_stats(lock_rows=True, session=session)
```

**Flow:** try advisory lock (pg-only fast fail) → lock pool rows NOWAIT → compute `pool_slots_free = sum(max(0, pool["open"]))`, early-return when 0 → candidate query with `skip_locked` row locks on TIs → bulk QUEUED update → executor routing. A blocked scheduler skips enqueueing but continues DAG-run creation/progression in the same loop.
**Invariant:** Only ONE scheduler may convert SCHEDULED→QUEUED at a time (pool-slot arithmetic races otherwise); losing the lock must be non-blocking (busy schedulers just skip the tick) and must NOT emit the critical-section duration metric (`timer.stop(send=False)`) since it would skew latency percentiles.
**Probe:** `grep -c '55P03' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 1; direct test `airflow-core/tests/unit/jobs/test_scheduler_job.py::TestSchedulerJob::test_critical_section_enqueue_task_instances` (:3274).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "advisory lock scheduler critical section postgresql", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pool-rows-as-mutex with NOWAIT semantics and the metric-suppression-on-lock-busy rule. Adapt the advisory lock to your DB (it exists to avoid littering Postgres logs with lock-timeout errors). Omit MySQL hint strings (`USE INDEX (ti_state)`).
