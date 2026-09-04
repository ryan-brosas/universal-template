<!-- capsule-v2 -->
# Stale concurrency-slot reaper — how are global concurrency slots freed when a run ends without releasing them?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What guarantees a crashed run's concurrency slots eventually free up, and what config gates the sweep?

## Time-delayed reclamation of finished runs' slots
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/monitoring/concurrency.py:execute_concurrency_slots_iteration` (lines 14-53).
**Signature:** `def execute_concurrency_slots_iteration(workspace_process_context, logger, _debug_crash_flags=None) -> Iterator[SerializableErrorInfo | None]`; `RUN_BATCH_SIZE = 1000`.
**Data Shape:** Config: `run_monitoring_settings["free_slots_after_run_end_seconds"]` (0/None disables); requires `event_log_storage.supports_global_concurrency_limits`. Slot occupancy source: `instance.event_log_storage.get_concurrency_run_ids()` (runs currently holding slots).

### Decisive source
```python
now = get_current_datetime()
run_records = instance.get_run_records(
    filters=RunsFilter(
        run_ids=list(run_ids),
        statuses=FINISHED_STATUSES,
        updated_before=(now - datetime.timedelta(seconds=timeout_seconds)),
    ),
    limit=RUN_BATCH_SIZE,
)
for run_record in run_records:
    if run_record.end_time + timeout_seconds < now.timestamp():
        freed_slots = instance.event_log_storage.free_concurrency_slots_for_run(
            run_record.dagster_run.run_id
        )
        if freed_slots:
            logger.info(
                f"Freed {freed_slots} slots for run {run_record.dagster_run.run_id} with status"
                f" {run_record.dagster_run.status}"
            )
        yield
```

**Flow:** The MonitoringDaemon runs this AFTER `execute_run_monitoring_iteration` every tick (`daemon.py:MonitoringDaemon.run_iteration` :403-408: `yield from execute_run_monitoring_iteration(...)` then `yield from execute_concurrency_slots_iteration(...)`). Sweep = runs holding slots ∩ finished status ∩ not updated recently; double condition (SQL `updated_before` filter AND in-Python `end_time + timeout < now`) then frees each run's slots one at a time with a yield between iterations (heartbeat liveness for large batches).
**Invariant:** Slots are NOT freed at the moment a run finishes — they persist for the grace window (so an immediately-retried successor can't race a still-cleaning-up predecessor) — and the reaper is idempotent: freeing an already-free slot returns 0 and logs nothing. A porter who frees slots synchronously on terminal event will break retry-race safety.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_concurrency_daemon.py` (concurrency slot lifecycle incl. freeing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "free_concurrency_slots_for_run get_concurrency_run_ids", limit: 10 });
```

## Verdict
Adopt delayed-idempotent slot reaping as a daemon sweep rather than an inline release; adapt the storage capability flags to your schema; omit the global-concurrency-limit storage internals (separate seam). Test coverage via upstream test_concurrency_daemon.py.
