<!-- capsule-v2 -->
# Starvation-filter retry ladder — how does the picker find tasks behind blocked high-priority ones?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** When a pool/dag/task hits its concurrency limit, how does the same tick still schedule lower-priority work instead of starving it forever?

## Four starvation sets grown in-loop, re-applied as SQL filters each round
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:_executable_task_instances_to_queued` (728–1048).
**Signature:** inner `for loop_count in itertools.count(start=1):` re-query loop.
**Data Shape:** Four sets: `starved_pools: set[str]`, `starved_dags: set[str]`, `starved_tasks: set[(dag_id,task_id)]`, `starved_tasks_task_dagrun_concurrency: set[(dag_id,run_id,task_id)]`. Each iteration snapshots their sizes, rebuilds the query with `.not_in(...)` filters for each set, examines up to `max_tis` rows, adds newly-starved keys, and decides continuation.

### Decisive source
```python
if starved_pools:
    query = query.where(TI.pool.not_in(starved_pools))
if starved_dags:
    query = query.where(TI.dag_id.not_in(starved_dags))
if starved_tasks:
    query = query.where(tuple_(TI.dag_id, TI.task_id).not_in(starved_tasks))
...
is_done = executable_tis or len(task_instances_to_examine) < max_tis
found_new_filters = (
    len(starved_pools) > num_starved_pools
    or len(starved_dags) > num_starved_dags
    or len(starved_tasks) > num_starved_tasks
    or len(starved_tasks_task_dagrun_concurrency) > num_starved_tasks_task_dagrun_concurrency
)
if is_done or not found_new_filters:
    break
```

**Flow:** query ordered by `(-priority_weight, logical_date, map_index)` → walk candidates applying per-TI checks (pool open slots, `pool_slots <= open`, dag max_active_tasks via ConcurrencyMap, task concurrency, executor slot availability) → blocked TIs add starvation entries → if nothing executable BUT new filters appeared, re-query with those excluded (a blocked top-priority task no longer masks lower-priority runnable ones) → stop when any executable found, fewer than max_tis returned, or no new starvation discovered.
**Invariant:** The loop must terminate: it repeats only while the previous round discovered NEW starved keys AND produced nothing executable; in-memory counters (`open_slots -= pool_slots`, ConcurrencyMap increments) keep subsequent checks within the SAME tick consistent without re-querying counts.
**Probe:** `grep -c 'is_done or not found_new_filters' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 1; direct tests `test_find_executable_task_instances_pool` (:1532), `..._backfill` (:1438) in `airflow-core/tests/unit/jobs/test_scheduler_job.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "starved_pools starved_tasks executable_task_instances", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the starvation-set + re-query pattern for priority pickers with hierarchical limits. Adapt the four dimensions to your domain's limit axes. Omit the pool.starving_tasks gauge tagging (multi-team specific).
