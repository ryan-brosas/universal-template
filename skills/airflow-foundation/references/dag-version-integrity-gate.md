<!-- capsule-v2 -->
# DAG-version integrity gate — when must a running DAG run be re-verified against the latest code version?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** A DAG file changed after a run started — when does the scheduler pay for `verify_integrity` and what does it migrate?

## Membership probe first, bulk migration second
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:_verify_integrity_if_dag_changed` (3062–3098).
**Signature:** `_verify_integrity_if_dag_changed(self, dag_run, session) -> bool` (False = DAG disappeared, skip scheduling this run this tick).
**Data Shape:** Fast path: `DagVersion.get_latest_version(dag_id)` then `dag_run.check_version_id_exists_in_dr(latest.id)` — an O(1)-ish membership check on the run's pinned versions. Slow path taken only on miss.

### Decisive source
```python
if dag_run.check_version_id_exists_in_dr(latest_dag_version.id, session=session):
    self.log.debug("DAG %s not changed structure, skipping dagrun.verify_integrity", dag_run.dag_id)
    return True
# Refresh the DAG
...
session.execute(
    update(TI)
    .where(TI.dag_id == dag_run.dag_id, TI.run_id == dag_run.run_id, TI.state.in_(State.unfinished))
    .values(dag_version_id=latest_dag_version.id),
    execution_options={"synchronize_session": False},
)
# Expire task_instances relationship so next access fetches fresh data from DB
session.expire(dag_run, ["task_instances"])
# Verify integrity also takes care of session.flush
dag_run.verify_integrity(dag_version_id=latest_dag_version.id, session=session)
```

**Flow:** per-run gate inside `_schedule_dag_run` (skipped entirely for bundle-version-pinned runs: `if not dag_run.bundle_version and not self._verify...`) → membership miss means the run predates the newest DAG version → refresh serialized DAG → BULK re-point every unfinished TI's dag_version_id (loading all TIs into memory was measured "very very slow", #11147) → expire cached relationship → full `verify_integrity` reconciles added/removed tasks. Callers treat False as "DAG gone; skip silently".
**Invariant:** verify_integrity is too slow per-tick per-run; it must be gated behind a cheap staleness probe or scheduler throughput collapses on large DAGs. Unfinished TIs migrate to the new version atomically in SQL; finished TIs keep their historical version.
**Probe:** `grep -c 'check_version_id_exists_in_dr' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 1; graph anchor line-exact at :3062 via `search_graph` query "_verify_integrity_if_dag_changed dag_version bulk update unfinished".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "_verify_integrity_if_dag_changed dag_version bulk update unfinished", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt probe-then-reconcile for hot-path integrity checks under code versioning. Adapt to your own version/manifest model. Omit if your runs are immutable-by-construction.
