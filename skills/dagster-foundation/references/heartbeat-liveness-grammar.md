<!-- capsule-v2 -->
# Heartbeat liveness grammar — when does the UI/CLI consider a daemon dead, and what exactly is written?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What formula decides daemon health, what is the difference between "live" and "healthy", and which fields must a heartbeat row carry for a portable port?

## Health = timestamp + interval + tolerance
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/controller.py:get_daemon_statuses` (lines 424-470), constants :35-59; `types.py:DaemonHeartbeat` (:26-52); CLI `cli/__init__.py:liveness_check_command` (:127-133).
**Signature:** `def get_daemon_statuses(instance, daemon_types, curr_time_seconds=None, ignore_errors=False, heartbeat_interval_seconds=30.0, heartbeat_tolerance_seconds=1800.0) -> Mapping[str, DaemonStatus]`.
**Data Shape:** `DaemonHeartbeat(timestamp: float, daemon_type: str, daemon_id: str|None, errors: Sequence[SerializableErrorInfo]|None)`; `DaemonStatus(daemon_type, required, healthy: bool|None, last_heartbeat)`. Constants: heartbeat every 30s (`DEFAULT_HEARTBEAT_INTERVAL_SECONDS`), tolerance 1800s (`DEFAULT_DAEMON_HEARTBEAT_TOLERANCE_SECONDS`, overridable via env `DAGSTER_DAEMON_HEARTBEAT_TOLERANCE`), error window 300s (`DEFAULT_DAEMON_ERROR_INTERVAL_SECONDS`).

### Decisive source
```python
maximum_tolerated_time = (
    hearbeat_timestamp + heartbeat_interval_seconds + heartbeat_tolerance_seconds
)
healthy = curr_time_seconds <= maximum_tolerated_time

if not ignore_errors and latest_heartbeat.errors:
    healthy = False
```
Plus the required/not-required ladder at :441-450: a daemon_type not in `instance.get_required_daemon_types()` gets `healthy=None, required=False`; a missing heartbeat row gets `healthy=False, last_heartbeat=None`.

**Flow:** Writer side (`daemon.py:_check_add_heartbeat` :147-211): prune errors older than the 300s error window → skip writing entirely if `instance.daemon_skip_heartbeats_without_errors` and no errors (a "quiet-when-healthy" mode that flips the health semantics to error-reporting only) → throttle writes by local `_last_heartbeat_time` → detect a second competing writer ("Another %s daemon is still sending heartbeats... multiple daemon processes running at once, which is not supported") by comparing the stored row's `daemon_id` with this process's uuid → write. Reader side: two public predicates — `all_daemons_live()` (ignore_errors=True; used by the `dagster-daemon liveness-check` CLI / k8s probe) vs `all_daemons_healthy()` (errors make it unhealthy). The controller's own watchdog (`check_daemon_heartbeats` :261-273) only WARNS about stale-heartbeat daemons — it never kills them; only a dead thread triggers `raise Exception("Stopped dagster-daemon process due to threads no longer running")`.
**Invariant:** Health math must be `last_heartbeat + heartbeat_interval + tolerance >= now`; the extra interval term means a daemon that skips ONE write is never immediately flagged. `errors` non-empty ⇒ unhealthy under `all_daemons_healthy` but still live.
**Probe:** `integration_tests/test_suites/daemon-test-suite/test_dagster_daemon_health.py::test_transient_heartbeat_failure` (health recovers after transient failure); `python_modules/dagster/dagster_tests/daemon_tests/test_types.py::test_heartbeat_backcompat` (legacy enum-typed heartbeats deserialize via `before_unpack`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "get_daemon_statuses add_daemon_heartbeat DaemonStatus liveness", limit: 10 });
```

## Verdict
Adopt the three-term deadline formula and the live-vs-healthy split (liveness probes should use ignore_errors=True or a crashing daemon flaps your orchestrator); adapt storage of heartbeats (Dagster uses its KV/run store); omit the serdes back-compat unpacker if you have no legacy rows.
