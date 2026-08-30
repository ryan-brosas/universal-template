<!-- capsule-v2 -->
# DAG-run timeout purge — how are unfinished tasks closed when dagrun_timeout fires?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** When a run exceeds `dagrun_timeout`, what states do its straggler tasks get and which TI feeds the failure callback?

## Skip unfinished TIs, pick last-started as relevant_ti, reload before callback
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:_schedule_dag_run` (2949–3019).
**Signature:** `_schedule_dag_run(self, dag_run, session) -> DagCallbackRequest | None`.
**Data Shape:** Timeout condition: `dag_run.start_date and dag.dagrun_timeout and start_date < utcnow() - dagrun_timeout`. Unfinished set = `state IN State.unfinished OR state IS NULL`; `last_unfinished_ti = max(..., key=lambda ti: ti.start_date or make_aware(datetime.min), default=None)`.

### Decisive source
```python
for task_instance in unfinished_task_instances:
    task_instance.state = TaskInstanceState.SKIPPED
    session.merge(task_instance)
session.flush()
...
callback_to_execute = dag_run.produce_dag_callback(
    dag=dag,
    success=False,
    relevant_ti=last_unfinished_ti,
    reason="timed_out",
    execute=False,
)
```

**Flow:** mark run FAILED via `set_state` → SKIP (not FAIL) every unfinished TI — skips don't count as failures for downstream trigger rules or retry accounting → flush → recompute finished-state bookkeeping (`_set_exceeds_max_active_runs`) → RE-SELECT the DagRun with eager-loaded consumed_asset_events because `produce_dag_callback` serializes context that lazy-loads would fail on after commit boundaries → build the callback request WITHOUT executing (scheduler never runs user code; the request goes to the executor via `executor.send_callback`). `produce_dag_callback` additionally drops `relevant_ti` when `dag_version_id IS NULL` (pre-versioning rows crash Pydantic validation).
**Invariant:** Timed-out tasks are SKIPPED, not failed — mapping them to FAILED changes downstream semantics (default trigger rules treat skipped differently) and double-counts failures. Callback requests must be data-complete (bundle/version info resolved server-side) because the processor executes them against pinned code versions.
**Probe:** `grep -c 'reason="timed_out"' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 1; covered by scheduler suite `test_scheduler_job.py` timed-out run cases (search `dagrun_timeout`); direct graph anchor `_schedule_dag_run` :2926.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "_schedule_dag_run update_state schedule_tis callback_to_run", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt timeout-purge-as-SKIP plus data-complete deferred callbacks. Adapt the version/bundle fields to your own code-pinning scheme. Omit asset-event eager loading if you lack asset-aware runs.
