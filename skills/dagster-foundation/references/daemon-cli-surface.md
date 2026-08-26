<!-- capsule-v2 -->
# Daemon CLI surface & required-daemon derivation — which commands must a daemon binary expose and how does instance config select daemons?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What is the minimal operator interface for the daemon process, and how do daemons get instantiated from instance settings?

## run / liveness-check / wipe / debug over a config-derived factory
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/cli/__init__.py` (whole file; `run_command` :75-101, `_daemon_run_command` :104-120, `liveness_check_command` :127-133) + `controller.py:create_daemons_from_instance` (:66-70), `create_daemon_of_type` (:357-384).
**Signature:** `def create_daemons_from_instance(instance: DagsterInstance) -> Sequence[DagsterDaemon]` = `[create_daemon_of_type(t, instance) for t in instance.get_required_daemon_types()]`.
**Data Shape:** Eight daemon types keyed by string: SCHEDULER, SENSOR, QUEUED_RUN_COORDINATOR, BACKFILL, MONITORING, EVENT_LOG_CONSUMER, ASSET, FRESHNESS_DAEMON — each constructed with knobs read from the instance (e.g. `QueuedRunCoordinatorDaemon(interval_seconds=instance.run_coordinator.dequeue_interval_seconds)`, `AssetDaemon(settings=instance.get_auto_materialize_settings(), pre_sensor_interval_seconds=instance.auto_materialize_minimum_interval_seconds or 30)`).

### Decisive source
```python
def liveness_check_command() -> None:
    with get_instance_for_cli() as instance:
        if all_daemons_live(instance, heartbeat_tolerance_seconds=_get_heartbeat_tolerance()):
            click.echo("Daemon live")
        else:
            click.echo("Daemon(s) not running")
            sys.exit(1)
```
And the run entrypoint wiring: `run_command` composes `interrupt_on_ipc_shutdown_message(shutdown_pipe)` + `capture_interrupts()` + instance context, then `daemon_controller_from_instance(...)` with `heartbeat_tolerance_seconds=_get_heartbeat_tolerance()` (env `DAGSTER_DAEMON_HEARTBEAT_TOLERANCE`) and finally blocks in `controller.check_daemon_loop()`. Unknown daemon type ⇒ `raise Exception(f"Unexpected daemon type {daemon_type}")`.

**Flow:** `dagster-daemon run` → derive REQUIRED daemons purely from instance configuration (which storage/run-coordinator settings are active decide membership — e.g. QueuedRunCoordinator presence implies its daemon) → controller threads + watchdog loop. `liveness-check` is designed as an orchestrator probe: exit code 1 when any required daemon's heartbeat is stale (uses LIVE not HEALTHY semantics). `wipe` clears heartbeats; `debug heartbeat`/`heartbeat-dump` write/read a synthetic SensorDaemon heartbeat for storage round-trip diagnosis.
**Invariant:** Daemon MEMBERSHIP is derived, not enumerated by hand — porting means implementing `get_required_daemon_types()` correctly against your config, otherwise liveness probes check daemons that never run (or miss ones that do).
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_dagster_daemon.py` (required-daemon derivation scenarios).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "create_daemon_of_type get_required_daemon_types liveness_check_command", limit: 10 });
```

## Verdict
Adopt config-derived membership + the four-command operator surface (run/liveness/wipe/debug); adapt CLI framework and probe integration to your host; omit telemetry wrapper and IPC shutdown-pipe plumbing if not needed.
