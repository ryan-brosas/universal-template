<!-- capsule-v2 -->
# Crash-proof external_executor_id — why is the executor's task UUID assigned in the QUEUED bulk UPDATE?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How does a scheduler guarantee the external executor id (e.g. Celery task_id) exists before the TI row can be observed, so a crash between queueing and sending never orphans a task?

## UUID written atomically with state flip; read back via RETURNING
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:_executable_task_instances_to_queued` (1079–1143).
**Signature:** bulk `update(TI).where(filter_for_tis).values(**queued_values)` with optional `.returning(...)`.
**Data Shape:** `queued_values` = `{state: QUEUED, queued_dttm, queued_by_job_id}` plus `external_executor_id` when executors opt in via `pre_assigns_external_executor_id`. Three modes: all-executors-opt-in (unconditional uuid), mixed (SQL `CASE` on `TI.executor` name/alias, default-executor `NULL` case), none (column untouched).

### Decisive source
```python
# Pre-assign external_executor_id atomically with the QUEUED state so it
# survives a scheduler crash. ...
if pre_assign_executors == set(self.executors):
    queued_values["external_executor_id"] = random_db_uuid()
...
if get_dialect_name(session) == "postgresql":
    result = session.execute(queued_update.returning(TI.id, TI.external_executor_id))
    id_map = {row[0]: row[1] for row in result}
else:
    session.execute(queued_update)
    id_rows = session.execute(select(TI.id, TI.external_executor_id).where(filter_for_tis)).all()
    id_map = {row[0]: row[1] for row in id_rows}
for ti in executable_tis:
    ti.external_executor_id = id_map.get(ti.id)
```

**Flow:** DB-generated UUIDs must be read back onto the ORM objects BEFORE `make_transient(ti)` detaches them — the workload DTO (`ExecuteTask.make`) reads `ti.external_executor_id` after detachment. Postgres uses `UPDATE ... RETURNING`; MySQL/SQLite fall back to a follow-up SELECT because RETURNING requires SQLite ≥ 3.35.
**Invariant:** Never generate the id in Python after the commit — the whole point is that any observer of `state=QUEUED` also sees the same `external_executor_id`, so adoption/revoke by another scheduler references an id the broker actually knows.
**Probe:** `grep -c 'pre_assigns_external_executor_id' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 2; direct test `test_executable_task_instances_to_queued_sets_external_executor_id` at `airflow-core/tests/unit/jobs/test_scheduler_job.py:3156`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "external_executor_id pre_assign queued uuid RETURNING", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt assign-on-transition-with-readback for any externally-addressable work item. Adapt the dialect split to your stack. Omit the CASE-based mixed-executor routing unless you have per-task executor selection.
