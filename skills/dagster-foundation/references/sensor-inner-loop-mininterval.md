<!-- capsule-v2 -->
# Sensor 5s inner loop + min-interval gate — how do sensors evaluate continuously while the daemon machinery ticks at 30s?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** How can per-sensor cadence be decoupled from the daemon interval without starving heartbeats or one hot sensor starving others?

## Tighter inner loop, spacing enforced per sensor
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/sensor.py:execute_sensor_iteration_loop` (lines 345-395) with `MIN_INTERVAL_LOOP_TIME = 5` (:72), `is_under_min_interval` (:1259-1275), `get_elapsed` (:1278-1289), and the scheduling gate in `execute_sensor_iteration` (:464-468).
**Signature:** `def execute_sensor_iteration_loop(workspace_process_context, logger, shutdown_event, until=None, threadpool_executor=None, submit_threadpool_executor=None, instrument_elapsed=...) -> DaemonIterator`.
**Data Shape:** `get_elapsed` returns `now - max(last_tick_timestamp, last_tick_start_timestamp)` (None if neither set); a sensor is under min-interval when `0 < min_interval` and `elapsed < min_interval`. `mark_sensor_state_for_tick` stamps `last_tick_start_timestamp=now` BEFORE evaluation (so a long evaluation doesn't re-trigger) and clears `last_tick_success_timestamp`.

### Decisive source
```python
# docstring: Rather than relying on the daemon machinery to run the
# iteration loop every 30 seconds, sensors are continuously evaluated, every 5 seconds. We
# rely on each sensor definition's min_interval to check that sensor evaluations are spaced
# appropriately.
...
loop_duration = end_time - start_time
sleep_time = max(0, MIN_INTERVAL_LOOP_TIME - loop_duration)
shutdown_event.wait(sleep_time)
yield None
```
And in the threaded path (:474-492): "only allow one tick per sensor to be in flight" — skip when `sensor_tick_futures[selector_id]` exists and isn't done; else submit `_process_tick` (the generator drained to a list via `_process_tick = return_as_list(_process_tick_generator)` :663, "evaluate the tick immediately, but from within a thread. The main thread should be able to heartbeat").

**Flow:** loop every ≥5s → collect running sensors from workspace+states, skipping AUTOMATION-type sensors (`sensor.sensor_type.is_handled_by_asset_daemon` — those belong to the AssetDaemon) → shuffled round-robin across code locations (`shuffled_round_robin_by_key`, "so a single code location with many sensors cannot consistently push sensors from other code locations to the back of the thread pool queue") → per sensor: default-status DECLARED_IN_CODE state creation OR min-interval skip → submit/evaluate tick.
**Invariant:** The heartbeat contract holds because every path yields between units of work; the fairness contract holds because ordering is randomized round-robin, not input order; the correctness contract holds because `last_tick_start_timestamp` participates in elapsed math — measuring only completion time would double-fire slow sensors.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_daemon_utils.py::test_shuffled_round_robin_bykey_*` (5 tests: empty/single_group/preserves_membership/round_robin_pattern/heavy_group_does_not_starve_light).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "execute_sensor_iteration_loop is_under_min_interval get_elapsed", limit: 10 });
```

## Verdict
Adopt the two-timescale design (outer heartbeat cadence, inner work cadence) + start-timestamp-based spacing + randomized round-robin; adapt the 5s constant; omit the instrumentation hook stub. Round-robin util has direct unit tests upstream.
