<!-- capsule-v2 -->
# DAG-run creation budget — why create only 10 runs and examine only 20 per tick?

**Source:** Apache Airflow Apache-2.0 `main@a4b6b77e6832a0047d6857544a927b3108e7ed94`; Codebase Memory `ext-airflow`. **Question:** How does the scheduler split its per-tick time between creating new DAG runs and progressing existing ones?

## Capped creation + oldest-examined-first rotation
**Path/Symbol:** `airflow-core/src/airflow/jobs/scheduler_job_runner.py:_do_scheduling` docstring + flow (1985–2036); `DagRun.get_running_dag_runs_to_examine` (dagrun.py:747); creation via `_create_dag_runs_for_dags` (2460) honoring `max_dagruns_to_create_per_loop`.
**Signature:** `_do_scheduling(self, session) -> int` (number of TIs enqueued this iteration).
**Data Shape:** Defaults: `scheduler.max_dagruns_to_create_per_loop = 10`, `scheduler.max_dagruns_per_loop_to_schedule = 20`. Selection = "next n oldest" by `last_scheduling_decision` — runs NOT examined most recently.

### Decisive source
```python
# Since creating Dag Runs is a relatively time consuming process, we select only 10 dags by default ...
# By "next oldest", we mean hasn't been examined/scheduled in the most time.
# We don't select all dagruns at once, because the rows are selected with row locks, meaning
# that only one scheduler can "process them", even it is waiting behind other dags. Increasing this
# limit will allow more throughput for smaller DAGs but will likely slow down throughput for larger
# (>500 tasks.) DAGs
```

**Flow:** window-1 creates up to 10 new runs → `_start_queued_dagruns` promotes QUEUED→RUNNING → fetch ≤20 running runs ordered by scheduling staleness (row-locked so HA schedulers partition work naturally) → schedule each (`_schedule_all_dag_runs`) → critical section queues TIs. The whole tick returns `num_queued_tis` which drives idle detection and sleep in `_run_scheduler_loop`.
**Invariant:** Row locks make the examine-batch a mutual-exclusion unit — bigger batches hoard locks from HA peers and starve large DAGs; smaller batches waste more of the fixed per-tick overhead. Fairness comes from ordering on last_scheduling_decision, not from processing everything each pass.
**Probe:** `grep -c 'get_running_dag_runs_to_examine' airflow-core/src/airflow/jobs/scheduler_job_runner.py` → 1; direct test `test_multi_team_scheduling_loop_batch_optimization` at `airflow-core/tests/unit/jobs/test_scheduler_job.py:10580`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-airflow", query: "_do_scheduling max_dagruns create examine loop batch", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capped run-creation with staleness-ordered examination batches. Adapt the two knobs to your workload size. Omit asset/partitioned-run creation variants (separate plane).
