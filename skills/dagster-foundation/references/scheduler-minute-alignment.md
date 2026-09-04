<!-- capsule-v2 -->
# Scheduler minute-alignment + in-flight dedupe — how does the scheduler loop avoid double-ticking and busy-waiting?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What cadence does the scheduler daemon actually run at, and how are duplicate in-flight schedule evaluations prevented across iterations?

## Whole-minute sleep + per-schedule future map
**Path/Symbol:** `python_modules/dagster/dagster/_scheduler/scheduler.py:execute_scheduler_iteration_loop` (lines 194-266) with `_get_next_scheduler_iteration_time` (:158-162) and the threaded gate (:403-429).
**Signature:** `def _get_next_scheduler_iteration_time(start_time: float) -> float`; loop state: `scheduler_run_futures: dict[str, Future]`, `iteration_times: dict[str, ScheduleIterationTimes]`.
**Data Shape:** `ScheduleIterationTimes(cron_schedule, next_iteration_timestamp, last_iteration_timestamp)` with `should_run_next_iteration(schedule, now)`: cron string changed ⇒ always run; else `now >= next_iteration_timestamp`. `ERROR_INTERVAL_TIME = 5` post-error wait.

### Decisive source
```python
def _get_next_scheduler_iteration_time(start_time: float) -> float:
    # Wait until at least the next minute to run again, since the minimum granularity
    # for a cron schedule is every minute
    last_minute_time = start_time - (start_time % SECONDS_IN_MINUTE)
    return last_minute_time + SECONDS_IN_MINUTE
...
if schedule.selector_id in scheduler_run_futures:
    if scheduler_run_futures[schedule.selector_id].done():
        try:
            result = scheduler_run_futures[schedule.selector_id].result()
            iteration_times[schedule.selector_id] = result
        except Exception:
            # Log exception and continue on rather than erroring the whole scheduler loop
            DaemonErrorCapture.process_exception(...)
        del scheduler_run_futures[schedule.selector_id]
    else:
        # only allow one tick per schedule to be in flight
        continue

previous_iteration_times = iteration_times.get(schedule.selector_id)
if (
    previous_iteration_times
    and not previous_iteration_times.should_run_next_iteration(
        schedule, end_datetime_utc.timestamp()
    )
):
    # Not enough time has passed for this schedule, don't bother creating a thread
    continue
```

**Flow:** each outer pass aligns its wake-up to the next whole-minute boundary (+0.001s epsilon "to be sure that we're past the start of the minute") → error shortens the next wait to min(now+5s, next minute) → per running schedule: harvest finished futures (exceptions logged not raised), skip schedules with a future still in flight, skip those whose `ScheduleIterationTimes` say it isn't time yet → submit evaluation. Cron-string change forces immediate re-evaluation so edits take effect within a minute.
**Invariant:** At most ONE in-flight tick per schedule selector id — overlapping long evaluations are skipped rather than queued, which bounds thread-pool saturation from pathological schedules. The minute alignment exists because sub-minute scheduling would double-fire cron times.
**Probe:** `python_modules/dagster/dagster_tests/scheduler_tests/test_scheduler_run.py` (iteration timing + future-harvest scenarios).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "_get_next_scheduler_iteration_time should_run_next_iteration scheduler_run_futures", limit: 10 });
```

## Verdict
Adopt minute-aligned wakes, single-in-flight-per-entity futures, and cron-change-forces-evaluation; adapt to your threading model; omit the delay-instrumentation hook stub.
