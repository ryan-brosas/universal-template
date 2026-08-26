<!-- capsule-v2 -->
# ConcurrencyMap slot taxonomy — which parked states hold a worker slot?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** Do DEFERRED / AWAITING_INPUT tasks consume pool slots and DAG-run active-task budget while waiting?

## Three counters, two different membership rules
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:ConcurrencyMap.load` (259–291); state sets in `airflow-core/src/airflow/ti_deps/dependencies_states.py` (21–52); pool math in `airflow-core/src/airflow/models/pool.py:Pool.slots_stats` (185–255).
**Signature:** `load(self, session)` fills `dag_run_active_tasks_map[(dag_id,run_id)]`, `task_concurrency_map[(dag_id,task_id)]`, `task_dagrun_concurrency_map[(dag_id,run_id,task_id)]` from one GROUP BY over ACTIVE_STATES.
**Data Shape:** `EXECUTION_STATES = {RUNNING, QUEUED}` (hold worker slots). `ACTIVE_STATES = EXECUTION ∪ {DEFERRED, AWAITING_INPUT}` (logically in-flight). `SCHEDULEABLE_STATES = {None, UP_FOR_RETRY, UP_FOR_RESCHEDULE}`.

### Decisive source
```python
# Always count towards task-level concurrency ... including DEFERRED.
self.task_concurrency_map[(dag_id, task_id)] += count
self.task_dagrun_concurrency_map[(dag_id, run_id, task_id)] += count
# Only count states that hold a worker slot towards DAG-run active tasks
# (max_active_tasks / worker slot accounting). DEFERRED and AWAITING_INPUT
# are in-flight but parked, holding no worker slot.
if state not in (TaskInstanceState.DEFERRED, TaskInstanceState.AWAITING_INPUT):
    self.dag_run_active_tasks_map[dag_id, run_id] += count
```

**Flow:** task-level limits (`max_active_tis_per_dag`, `max_active_tis_per_dagrun`) count DEFERRED/AWAITING_INPUT (a deferred task still logically occupies its concurrency allowance), while DAG-level `max_active_tasks` and pool accounting do NOT — pools count deferred only when `include_deferred=True`, and AWAITING_INPUT never reserves pool slots ("an open-ended human wait should not reserve one"). Pool open = `total - running - queued (- deferred?)`; `slots=-1` means infinity (`float("inf")`).
**Invariant:** Mixing these tiers breaks scheduling in opposite directions: counting deferred toward max_active_tasks starves DAGs whose tasks defer heavily; excluding them from task-concurrency lets duplicate sensor instances pile up. The candidate SQL additionally joins a live subquery `_get_current_dr_task_concurrency(EXECUTION_STATES)` so the max_active_tasks filter reflects DB truth even though ConcurrencyMap was loaded earlier in the tick.
**Probe:** `grep -c 'AWAITING_INPUT' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 6; direct test `airflow-core/tests/unit/models/test_pool.py::TestPool::test_open_slots_including_deferred` (:134).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "ConcurrencyMap deferred awaiting_input worker slot", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-tier state taxonomy and the two-axis accounting split. Adapt state names; keep the principle that human/parked waits never reserve compute slots. Omit Airflow's include_deferred opt-in column if your defers are short-lived.
