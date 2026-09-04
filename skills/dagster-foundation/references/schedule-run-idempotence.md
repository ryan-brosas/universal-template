<!-- capsule-v2 -->
# Schedule run idempotence by execution-time tag — how is "one run per schedule fire" guaranteed across crashes?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What prevents a retried tick (or a second daemon) from creating duplicate runs for the same scheduled execution time?

## Tag-query dedupe, namespace-filtered
**Path/Symbol:** `python_modules/dagster/dagster/_scheduler/scheduler.py:_get_existing_run_for_request` (lines 966-1001) + `_submit_run_request` existing-run branch (:783-798).
**Signature:** `def _get_existing_run_for_request(instance, remote_schedule, schedule_time: datetime.datetime, run_request: RunRequest) -> DagsterRun | None`.
**Data Shape:** Dedupe key = tags intersection of `DagsterRun.tags_for_schedule(remote_schedule)` + `{SCHEDULED_EXECUTION_TIME_TAG: schedule_time.astimezone(utc).isoformat()}` (+ RUN_KEY_TAG when the request carries one). The same tags are stamped at creation in `_create_scheduler_run` (:1030).

### Decisive source
```python
runs_filter = RunsFilter(tags=tags)
existing_runs = instance.get_runs(runs_filter)

# filter down to match schedule namespace (repository)
matching_runs = []
for run in existing_runs:
    # if the run doesn't have an origin consider it a match
    if run.remote_job_origin is None:
        matching_runs.append(run)
    # otherwise prevent the same named schedule (with the same execution time) across repos from effecting each other
    elif (
        remote_schedule.get_remote_origin().repository_origin.get_selector_id()
        == run.remote_job_origin.repository_origin.get_selector_id()
    ):
        matching_runs.append(run)

if not len(matching_runs):
    return None

return matching_runs[0]
```

**Flow:** before creating a run for a given cron time, tag-query for an existing one → found and NOT NOT_STARTED ⇒ log "Run %s already completed for this execution of %s" and skip launching (tick still records the run info; this is the crash-after-create-before-tick-success recovery path) → found but NOT_STARTED ⇒ reuse and submit → none ⇒ create with the exact same tag set so future queries find it. Sensor-side twin (`_get_or_create_sensor_run` in `_daemon/sensor.py` :1339-1375) mirrors this with run_key instead of execution time.
**Invariant:** The dedupe key must include the scheduled EXECUTION TIME (not wall-clock submit time) — retries happen later but target the same logical fire. Namespace filtering by repository selector-id prevents two identically-named schedules in different code locations from suppressing each other's runs.
**Probe:** `python_modules/dagster/dagster_tests/scheduler_tests/test_scheduler_run.py` (idempotence assertions across restart/retry scenarios).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "_get_existing_run_for_request SCHEDULED_EXECUTION_TIME_TAG tags_for_schedule", limit: 10 });
```

## Verdict
Adopt content-addressed run dedupe via deterministic tags + origin-scoped matching; adapt tag names to your storage; omit selector/origin plumbing if you have a single repo. Pinned by upstream scheduler tests.
