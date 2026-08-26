<!-- capsule-v2 -->
# Run-key dedupe fetch strategy — why does the sensor idempotence check query serially per run_key instead of one IN-clause?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What is the correct DB access pattern for "has this sensor already launched a run for this key?", including cross-repo name collisions?

## Serial per-key fetch + two-branch origin match
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/sensor.py:fetch_existing_runs` (lines 1292-1336) + `_get_or_create_sensor_run` (:1339-1375).
**Signature:** `def fetch_existing_runs(instance, remote_sensor, run_requests: Sequence[RunRequest]) -> dict[str, DagsterRun]` keyed by run_key.
**Data Shape:** Tags involved: `RUN_KEY_TAG`, `SENSOR_NAME_TAG`. Match validity = same sensor NAME plus (when origins exist) same repository SELECTOR.

### Decisive source
```python
# fetch runs from the DB with only the run key tag
# note: while possible to filter more at DB level with tags - it is avoided here due to observed
# perf problems
runs_with_run_keys: list[DagsterRun] = []
for run_key in run_keys:
    # do serial fetching, which has better perf than a single query with an IN clause, due to
    # how the query planner does the runs/run_tags join
    runs_with_run_keys.extend(
        instance.get_runs(filters=RunsFilter(tags={RUN_KEY_TAG: run_key}))
    )

# filter down to runs with run_key that match the sensor name and its namespace (repository)
valid_runs: list[DagsterRun] = []
for run in runs_with_run_keys:
    # if the run doesn't have a set origin, just match on sensor name
    if run.remote_job_origin is None and run.tags.get(SENSOR_NAME_TAG) == remote_sensor.name:
        valid_runs.append(run)
    # otherwise prevent the same named sensor across repos from effecting each other
    elif (
        run.remote_job_origin is not None
        and run.remote_job_origin.repository_origin.get_selector()
        == remote_sensor.get_remote_origin().repository_origin.get_selector()
        and run.tags.get(SENSOR_NAME_TAG) == remote_sensor.name
    ):
        valid_runs.append(run)

existing_runs: dict[str, DagsterRun] = {}
for run in valid_runs:
    tags = run.tags or {}
    # Guaranteed to have non-null run key because the source set of runs is `runs_with_run_keys`
    # above.
    run_key = check.not_none(tags.get(RUN_KEY_TAG))
    existing_runs[run_key] = run
```

**Flow:** gather keys → SERIAL single-tag queries (comment documents the measured perf reason: the runs/run_tags join planner degrades on compound tag IN-queries) → Python-side narrowing by sensor name + repo selector → dict keyed by run_key. `_get_or_create_sensor_run` then: hit with status ≠ NOT_STARTED ⇒ `SkippedSensorRun` ("A run already exists and was launched for this run key, but the daemon must have crashed before the tick could be updated"); hit with NOT_STARTED ⇒ reuse; miss ⇒ create AND backfill the dict ("Make sure that runs from the same tick are also unique by run key" :1372-1374).
**Invariant:** Dedupe must be scoped per (sensor name, repository namespace) — bare run-key matching would let identically-named sensors in different code locations suppress each other. Within-tick duplicates are prevented by mutating `existing_runs_by_key` as runs are created, not just reading pre-existing rows.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_dagster_daemon.py` (run-key skip scenarios across daemon tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "fetch_existing_runs RUN_KEY_TAG _get_or_create_sensor_run SkippedSensorRun", limit: 10 });
```

## Verdict
Adopt serial-per-key fetching with documented rationale and namespace-scoped matching; adapt to your tag schema/indexes — re-measure before "optimizing" into a single compound query; omit legacy no-origin branch if all your runs carry origins.
