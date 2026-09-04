<!-- capsule-v2 -->
# SensorLaunchContext error taxonomy — which tick failures bump the failure counters, and when does the cursor still advance?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** On a sensor evaluation error, what is written, and why do unreachable-code-server errors not count as failures?

## UserCodeUnreachable ≠ failure_count increment
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/sensor.py:SensorLaunchContext.__exit__` (lines 287-342) + `update_state` (:159-192) + `_write` (:232-282).
**Signature:** `def __exit__(self, exception_type, exception_value, traceback) -> None` — context manager wrapping each tick evaluation.
**Data Shape:** Tick fields mutated: `failure_count`, `consecutive_failure_count`, `error`, `skip_reason`, `cursor`, `origin_run_id`, `user_interrupted`. Success/skip reset BOTH counters to 0 (`update_state`: `if status in {SKIPPED, SUCCESS}: kwargs["failure_count"] = 0; kwargs["consecutive_failure_count"] = 0`).

### Decisive source
```python
if exception_value and not isinstance(exception_value, GeneratorExit):
    if isinstance(
        exception_value, (DagsterUserCodeUnreachableError, DagsterCodeLocationLoadError)
    ):
        try:
            raise DagsterUserCodeUnreachableError(
                f"Unable to reach the user code server for sensor {self._remote_sensor.name}."
                " Sensor will resume execution once the server is available."
            ) from exception_value
        except:
            error_data = DaemonErrorCapture.process_exception(...)
            self.update_state(
                TickStatus.FAILURE,
                error=error_data,
                # don't increment the failure count - retry until the server is available again
                failure_count=self._tick.failure_count,
                consecutive_failure_count=self._tick.consecutive_failure_count + 1,
            )
```
And `_write`'s cursor rule (:242-244): `should_update_cursor_and_last_run_key = (self._tick.status != TickStatus.FAILURE) or self._should_update_cursor_on_failure` — on failure the cursor/last_run_key are NOT advanced (the tick will be retried), unless a run-reaction explicitly set the flag ("Since run status sensors have side effects that we don't want to repeat, we still want to update the cursor, even though the tick failed" :1013-1015).

**Flow:** exit with KeyboardInterrupt ⇒ return silently (no write). Exit with GeneratorExit ⇒ no error recorded. Exit with user-code-unreachable class ⇒ FAILURE written but failure_count held constant (retry forever), consecutive_failure_count++ only. Any other exception ⇒ FAILURE with both counters incremented. Finally: `_write()` persists the tick and, for finished ticks, re-reads the instigator state fresh ("minimize the window of clobbering the sensor state"), updates last_run_key/cursor per the flag rule, stamps `last_tick_success_timestamp=None` on FAILURE else now, then purges old ticks per retention settings (`purge_ticks` per status/day-offset).
**Invariant:** The counter distinction drives retry policy elsewhere (`_get_evaluation_tick` retries FAILURE ticks only while `failure_count <= MAX_FAILURE_RESUBMISSION_RETRIES`) — so counting infra outages as failures would permanently poison sensors during code-server downtime. Cursor-on-failure defaults OFF to guarantee at-least-once evaluation.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_dagster_daemon.py` (sensor failure/retry scenarios; also scheduler twin behavior in scheduler_tests/test_scheduler_failure_recovery.py).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "SensorLaunchContext update_state should_update_cursor_on_failure", limit: 10 });
```

## Verdict
Adopt the two-counter error taxonomy with infra-error exemption and hold-cursor-on-failure default; adapt the retryable-class list; omit serdes specifics of SerializableErrorInfo. Behavior pinned by upstream daemon tests requiring deps (blocked this window); source verified byte-exact.
