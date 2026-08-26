<!-- capsule-v2 -->
# Schedule catch-up window machine — how does the cron scheduler decide which missed tick times to run after downtime?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** Given a cron schedule that fell behind (daemon down, or newly started), which execution times become ticks and which are dropped?

## start_timestamp fold + tail-truncation catch-up
**Path/Symbol:** `python_modules/dagster/dagster/_scheduler/scheduler.py:launch_scheduled_runs_for_schedule_iterator` (lines 548-762), constants :61-77 (`LAST_ITERATION_CHECKPOINT_INTERVAL_SECONDS=3600` env `DAGSTER_SCHEDULE_CHECKPOINT_INTERVAL_SECONDS`, jitter 600s).
**Signature:** `def launch_scheduled_runs_for_schedule_iterator(...) -> Generator[SerializableErrorInfo | ScheduleIterationTimes | None, None, None]`.
**Data Shape:** Inputs: `instigator_data.start_timestamp` (schedule enabled-at), `last_iteration_timestamp` (persisted hourly checkpoint), in-memory `ScheduleIterationTimes.last_iteration_timestamp`; latest tick row. Output: `tick_times: list[datetime]` to evaluate now, plus `next_iteration_timestamp` for sleep scheduling.

### Decisive source
```python
if latest_tick:
    if latest_tick.status == TickStatus.STARTED or (
        latest_tick.status == TickStatus.FAILURE
        and latest_tick.failure_count <= max_tick_retries
    ):
        # Scheduler was interrupted while performing this tick, re-do it
        start_timestamp_utc = max(
            start_timestamp_utc,
            latest_tick.timestamp,
            instigator_data.last_iteration_timestamp or 0.0,
            in_memory_last_iteration_timestamp or 0.0,
        )
    else:
        start_timestamp_utc = max(
            start_timestamp_utc,
            latest_tick.timestamp + 1,
            ...
        )
...
for next_time in remote_schedule.execution_time_iterator(start_timestamp_utc):
    next_tick_timestamp = next_time.timestamp()
    if next_tick_timestamp > now_timestamp:
        next_iteration_timestamp = next_tick_timestamp
        break
    tick_times.append(next_time)

if not remote_schedule.partition_set_name and len(tick_times) > 1:
    logger.warning(f"{schedule_name} has no partition set, so not trying to catch up")
    tick_times = tick_times[-1:]
elif len(tick_times) > max_catchup_runs:
    logger.warning(f"{schedule_name} has fallen behind, only launching {max_catchup_runs} runs")
    tick_times = tick_times[-max_catchup_runs:]
```

**Flow:** fold four candidate lower bounds (start_timestamp / last tick (+1 if finished) / persisted checkpoint / in-memory checkpoint) into `start_timestamp_utc` → iterate cron times forward collecting every time ≤ now → catch-up policy: partition-less schedules run ONLY the most recent missed time ("not trying to catch up"); partitioned schedules keep at most the LAST `max_catchup_runs` times (most recent wins — old gaps are skipped, not queued oldest-first) → each kept time becomes a tick; a tick whose timestamp equals an existing FAILURE/STARTED tick is retried/resumed in place (:661-668). After the sweep, `_write_and_get_next_checkpoint_timestamp` persists `last_iteration_timestamp` at most hourly + random jitter "so that threads won't all come back at the exact same time".
**Invariant:** Catch-up is bounded and biased to recency: unbounded backfills never happen by accident; the checkpoint exists so a cron-string CHANGE can't resurrect ticks older than ~1h ("if the cron schedule changes... we don't try to backfill schedule ticks from the start of the schedule"). Sleep alignment waits to the next whole minute (`_get_next_scheduler_iteration_time`, :158-162) since cron granularity is minutes.
**Probe:** `python_modules/dagster/dagster_tests/scheduler_tests/test_scheduler_run.py` (49 tests incl. catch-up & restart cases) + test_scheduler_failure_recovery.py.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "execution_time_iterator max_catchup_runs launch_scheduled_runs_for_schedule", limit: 10 });
```

## Verdict
Adopt the four-way lower-bound fold, tail-truncated catch-up, and hourly+jittered checkpoint; adapt cron iteration + partition semantics to your engine; omit the partition-set-specific branches if you have no partitioned schedules. Direct tests cover recovery scenarios upstream.
