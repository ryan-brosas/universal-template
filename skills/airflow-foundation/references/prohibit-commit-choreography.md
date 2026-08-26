<!-- capsule-v2 -->
# prohibit_commit transaction choreography — how does one scheduler tick batch its writes?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** Why does the scheduler wrap phases in commit prohibitions and where exactly are the two commits per tick?

## Two guarded windows per `_do_scheduling`; callbacks sent AFTER commit
**Path/Symbol:** `airflow-core/src/airflow/models/dagrun.py` callers in `airflow-core/src/airflow/jobs/scheduler_job_runner.py:_do_scheduling` (1985–2085); guard impl `airflow-core/src/airflow/utils/sqlalchemy.py:prohibit_commit` (661–680).
**Signature:** `with prohibit_commit(session) as guard:` … `guard.commit()`; `CommitProhibitorGuard.commit()`.
**Data Shape:** Window 1 = create DAG runs + start queued runs + schedule all runs (state progression). Window 2 = critical-section enqueue (SCHEDULED→QUEUED + executor send). Between them: expunge_all + callback dispatch.

### Decisive source
```python
callback_tuples = self._schedule_all_dag_runs(guard, dag_runs, session)

# Send the callbacks after we commit to ensure the context is up to date when it gets run
...
for dag_run, callback_to_run in callback_tuples:
    ...
with prohibit_commit(session) as guard:
    # Without this, the session has an invalid view of the DB
    session.expunge_all()
```

**Flow:** conf reads happen in `__init__` because MetadataMetastoreBackend access mid-window triggers `UNEXPECTED COMMIT - THIS WILL BREAK HA LOCKS`; `_schedule_all_dag_runs` lets DBAPIError propagate to `@retry_db_transaction` but swallows other exceptions per-run so one bad run can't kill the batch; guard.commit() is explicit INSIDE the window — ORM flushes are fine but COMMIT raises until released. Callback requests are collected during window 1 and dispatched only after its commit so downstream processors read committed state.
**Invariant:** An HA lock held across an unexpected commit is lost silently — any code path that might touch the metadata DB through a different session/backend must be kept OUT of the windows (hence init-time config caching). Sessions between windows must be expunged or stale identity-map objects corrupt window 2's arithmetic.
**Probe:** `grep -c 'prohibit_commit(session)' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 2; direct tests `test_prohibit_commit` (:183) + `test_prohibit_commit_specific_session_only` (:198) in `airflow-core/tests/unit/utils/test_sqlalchemy.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "prohibit_commit guard commit scheduling", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt phase-scoped commit suppression with post-commit side-effect dispatch. Adapt the guard mechanism to your session framework. Omit the multi-session internal-API variant documented in JOB_LIFECYCLE.md.
