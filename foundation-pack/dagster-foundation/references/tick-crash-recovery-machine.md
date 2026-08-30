<!-- capsule-v2 -->
# Tick crash-recovery state machine — what happens to a sensor tick interrupted mid-run-submission?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** How do you make "evaluate then launch N runs" atomic-ish when the daemon can die between any two launches?

## Reserved run-ids + resume-or-skip ladder
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/sensor.py:_get_evaluation_tick` (lines 508-582), `_handle_run_requests_and_automation_condition_evaluations` (:1074-1125), `_resume_tick` (:768-808); constants :74-83.
**Signature:** `def _get_evaluation_tick(instance, sensor, instigator_data, evaluation_timestamp, logger) -> InstigatorTick`; constants `MAX_TIME_TO_RESUME_TICK_SECONDS = 60*60*24`, `MAX_FAILURE_RESUBMISSION_RETRIES = 1`, `FINISHED_TICK_STATES = [SKIPPED, SUCCESS, FAILURE]`.
**Data Shape:** The tick row carries `unsubmitted_run_ids_with_requests` (reserved-but-unlaunched work) plus run_requests/reserved_run_ids written via `context.set_run_requests(...)` BEFORE submissions start.

### Decisive source
```python
if most_recent_tick.status == TickStatus.STARTED:
    # if the previous tick was interrupted before it was able to request all of its runs,
    # and it hasn't been too long, then resume execution of that tick
    if (
        evaluation_timestamp - most_recent_tick.timestamp <= MAX_TIME_TO_RESUME_TICK_SECONDS
        and has_unrequested_runs
    ):
        logger.warn(
            f"Tick {most_recent_tick.tick_id} was interrupted part-way through, resuming"
        )
        return most_recent_tick

    else:
        # previous tick won't be resumed - move it into a SKIPPED state so it isn't left
        # dangling in STARTED, but don't return it
        logger.warn(f"Moving dangling STARTED tick {most_recent_tick.tick_id} into SKIPPED")
        most_recent_tick = most_recent_tick.with_status(status=TickStatus.SKIPPED)
        instance.update_tick(most_recent_tick)
elif (
    most_recent_tick.status == TickStatus.FAILURE
    and most_recent_tick.tick_data.failure_count <= MAX_FAILURE_RESUBMISSION_RETRIES
    and has_unrequested_runs
):
    logger.info(f"Retrying failed tick {most_recent_tick.tick_id}")
    return instance.create_tick(...)
```
And the reservation write (:1107-1111): "# update cursor while reserving the relevant work, as now if the tick fails we will still submit # the requested runs" — `context.set_run_requests(run_requests, reserved_run_ids, cursor)` persists BEFORE any submit.

**Flow:** reserve ids → persist tick with unsubmitted set → submit each (run-key idempotence check via `fetch_existing_runs` + `_get_or_create_sensor_run`: existing non-NOT_STARTED run for that key ⇒ `SkippedSensorRun`) → on daemon death mid-way: next evaluation finds latest tick STARTED with unsubmitted work ⇒ RESUMES the same tick (freshness window 24h; older ⇒ moved to SKIPPED so it never dangles in STARTED) → FAILURE ticks get exactly ONE resubmission retry (only when unsubmitted work remains). Mid-submission stop by user: `_submit_run_requests` checks `context.sensor_is_enabled()` every `check_after_runs_num` submissions and marks `user_interrupted=True` ⇒ tick SKIPPED with reason "Sensor manually stopped mid-iteration." — deliberately SKIPPED (not SUCCESS) so restart does NOT re-submit the same runs.
**Invariant:** Run creation must be idempotent per (tick-reserved-id, run_key): reserved ids are minted up front and persisted before launching, so a crashed submission leaves recoverable evidence instead of orphaned or duplicated runs.
**Probe:** `integration_tests/test_suites/daemon-test-suite/test_daemon.py::test_heartbeat` neighborhood + dagster_tests/daemon_tests/test_dagster_daemon.py (tick interruption/resume scenarios).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "_get_evaluation_tick _resume_tick unsubmitted_run_ids_with_requests", limit: 10 });
```

## Verdict
Adopt reserve-persist-submit-resume ordering and the 24h resume horizon with dangling-tick skip; adapt tick storage shape; omit automation-evaluation persistence branches specific to schedule storage capability flags. Coverage caveat: full behavior suite is integration-level (needs running instance); source verified byte-exact at pin.
