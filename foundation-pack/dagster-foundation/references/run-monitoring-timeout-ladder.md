<!-- capsule-v2 -->
# Run monitoring timeout ladder — who fails runs that never start, never cancel, or run too long?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** How does a watchdog daemon detect and terminate wedged runs across the STARTING / STARTED / CANCELING lifecycle, with per-run override?

## One sweep, three status-specific monitors
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/monitoring/run_monitoring.py:execute_run_monitoring_iteration` (lines 174-223), `monitor_starting_run` (:28-67), `monitor_canceling_run` (:70-105), `monitor_started_run` (:113-171), `check_run_timeout` (:226-275), `_force_mark_as_failed` (:278-289).
**Signature:** `def execute_run_monitoring_iteration(workspace_process_context, logger, _debug_crash_flags=None) -> Iterator[SerializableErrorInfo | None]`; per-run dispatch by status.
**Data Shape:** Instance settings: `run_monitoring_start_timeout_seconds`, `run_monitoring_max_runtime_seconds`, `run_monitoring_cancel_timeout_seconds`, `run_monitoring_max_resume_run_attempts`; poll interval from `MonitoringDaemon(interval_seconds=instance.run_monitoring_poll_interval_seconds)`. Sweep set: `IN_PROGRESS_RUN_STATUSES + [CANCELING, NOT_STARTED]`. Per-run tag override: `dagster/max_runtime_seconds`.

### Decisive source
```python
max_time_str = run_record.dagster_run.tags.get(
    MAX_RUNTIME_SECONDS_TAG, run_record.dagster_run.tags.get("dagster/max_runtime_seconds")
)
if max_time_str:
    try:
        max_time = float(max_time_str)
    except ValueError:
        logger.warning(f"Invalid max runtime value: {max_time_str}")
        max_time = None
else:
    max_time = default_timeout_seconds

if not max_time:
    return

if (
    run_record.start_time is not None
    and get_current_timestamp() - run_record.start_time > max_time
):
    ...
    instance.report_run_canceling(run_record.dagster_run, message=f"Canceling due to exceeding maximum runtime of {int(max_time)} seconds.")
    try:
        if instance.run_launcher.terminate(run_id=run_record.dagster_run.run_id):
            instance.report_run_failed(...)
    except: ...          # engine event "Exception while attempting to terminate run..."
    _force_mark_as_failed(instance, run_record.dagster_run.run_id)
```

**Flow:** STARTING/NOT_STARTED past `start_timeout` ⇒ `report_run_failed(..., JobFailureData(error=None, failure_reason=RunFailureReason.START_TIMEOUT))` after best-effort `get_run_worker_debug_info`. CANCELING whose RUN_CANCELING event (searched descending, limit 1) is older than `cancel_timeout` ⇒ `report_run_canceled`. STARTED ⇒ health check ladder first (`check_run_worker_health`): unhealthy worker + status unchanged mid-loop + attempts < max ⇒ `instance.resume_run(run_id, workspace, attempt_number)` ("Launching a new run worker to resume run") and RETURN; attempts exhausted ⇒ fail; then `check_run_timeout`. Timeout termination ends with a re-read-and-force-fail so a run can never hang forever even when `terminate()` lies. Per-run exceptions are yielded as error events — one bad run never aborts the sweep.
**Invariant:** A value of 0 disables each timeout individually (`run_monitoring_start_timeout_seconds > 0` guards entry); an unparseable tag DISABLES the cap rather than falling back to global (deliberate: bad tag shouldn't kill long jobs). `_force_mark_as_failed` re-reads the record and only acts `if not reloaded_record.dagster_run.is_finished`.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_monitoring_daemon.py` (7 tests incl. start-timeout & max-runtime paths); integration_tests/test_suites/daemon-test-suite/monitoring_daemon_tests/.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "check_run_timeout monitor_started_run _force_mark_as_failed", limit: 10 });
```

## Verdict
Adopt the status-dispatched monitor trio + force-fail safety net + tag-overrides-global-with-parse-guard; adapt worker-health/resume plumbing to your launcher interface; omit Cloud's parallel worker-monitoring thread. Direct tests cover start/runtime timeouts upstream.
