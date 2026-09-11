<!-- capsule-v2 -->
# Daemon generator core loop — how does one process run eight independent daemons without any single long tick breaking liveness?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** When porting a multi-daemon scheduler, how do you structure the loop so an iteration can block for minutes while heartbeats keep flowing and errors never kill the process?

## Generator-driven cooperative loop
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/daemon.py:run_daemon_loop` (lines 88-145) + `_check_add_heartbeat` (147-211) + `IntervalDaemon.core_loop` (240-262).
**Signature:** `def run_daemon_loop(self, workspace_process_context: TContext, daemon_uuid: str, daemon_shutdown_event: Event, heartbeat_interval_seconds: float, error_interval_seconds: int) -> None` / `def core_loop(...) -> DaemonIterator` where `DaemonIterator = Generator[SerializableErrorInfo | SpanMarker | None, None, None]`.
**Data Shape:** Each daemon is a generator yielding three kinds of values: `None` (heartbeat checkpoint), `SerializableErrorInfo` (recorded into a bounded `deque(maxlen=DAEMON_HEARTBEAT_ERROR_LIMIT=5)` of `(error, timestamp)` tuples), and `SpanMarker.START_SPAN/END_SPAN` (tracing boundaries). The controller runs one OS thread per daemon (`controller.py:188-202`, threads named `dagster-daemon-<type>`, `daemon=True`) plus its own check loop thread.

### Decisive source
```python
try:
    result = next(daemon_generator)
    if isinstance(result, SerializableErrorInfo):
        self._errors.appendleft((result, get_current_datetime()))
except StopIteration:
    self._logger.error(
        "Daemon loop finished without raising an error - daemon loops should"
        " run forever until they are interrupted."
    )
    break
except Exception:
    error_info = DaemonErrorCapture.process_exception(...)
    self._errors.appendleft((error_info, get_current_datetime()))
    daemon_generator.close()
    # Wait a bit to ensure that errors don't happen in a tight loop
    daemon_shutdown_event.wait(_get_error_sleep_interval())
    daemon_generator = self.core_loop(workspace_process_context, daemon_shutdown_event)
```

**Flow:** `next(generator)` → on yield, first re-check/add heartbeat (`_check_add_heartbeat` is called before AND after each yield, lines 102-111 comment "Check to see if it's time to add a heartbeat initially and after each time the daemon yields") → on exception, close the poisoned generator, sleep `DAGSTER_DAEMON_CORE_LOOP_EXCEPTION_SLEEP_INTERVAL` (default 5s, `_get_error_sleep_interval` :47-48) via `shutdown_event.wait` (interruptible), rebuild a fresh generator from `core_loop`. `StopIteration` is treated as a defect ("loops should run forever") and exits the thread.
**Invariant:** Every blocking wait must go through `shutdown_event.wait(...)` or a yield point — never bare `time.sleep` in the inner loop — so SIGTERM/interrupt propagates within ~0.5s; every exception path appends to `self._errors` so the heartbeat carries recent errors instead of lying healthy.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_dagster_daemon.py` (generator restart-on-error behavior; also integration_tests/test_suites/daemon-test-suite/test_daemon.py::test_heartbeat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "run_daemon_loop core_loop IntervalDaemon heartbeat", limit: 10 });
```

## Verdict
Adopt the yield-checkpointed generator contract (heartbeats interleave with work at every yield) and the bounded error deque feeding heartbeats; adapt the interval constants and telemetry hooks to your host; omit the serdes-whitelisted `DaemonHeartbeat` wire format if your storage differs. Direct-test coverage exists upstream but requires dagster deps not installed in this checkout — deterministic probes stand in.
