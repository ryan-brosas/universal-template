<!-- capsule-v2 -->
# Controller watchdog ladder — what supervises the supervising threads, and in which order?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What does the daemon controller check, at what cadence, and which failure kills the process versus merely warning?

## Thread-death kills; stale heartbeats warn
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/controller.py:check_daemon_loop` (lines 293-321) with `check_daemon_threads` (:247-259), `check_workspace_freshness` (:275-291), `check_daemon_heartbeats` (:261-273), `_daemon_heartbeat_health` (:213-245), shutdown `__exit__` (:323-344).
**Signature:** `def check_daemon_loop(self) -> None` — the blocking main-loop body of the `dagster-daemon` process.
**Data Shape:** Cadence constants :47-59: `THREAD_CHECK_INTERVAL=5`, `HEARTBEAT_CHECK_INTERVAL=60`, `RELOAD_WORKSPACE_INTERVAL=60`, `DEFAULT_WORKSPACE_FRESHNESS_TOLERANCE=300`, `DAEMON_GRPC_SERVER_HEARTBEAT_TTL=20`.

### Decisive source
```python
while True:
    with raise_interrupts_as(KeyboardInterrupt):
        time.sleep(THREAD_CHECK_INTERVAL)
        self.check_daemon_threads()          # dead thread => raise => process dies

        last_workspace_update_time = self.check_workspace_freshness(last_workspace_update_time)

        if self._instance.daemon_skip_heartbeats_without_errors:
            continue                          # heartbeat checks skipped entirely

        now = get_current_timestamp()
        # Give the daemon enough time to send an initial heartbeat before checking
        if (
            (now - start_time) < 2 * self._heartbeat_interval_seconds
            or now - last_heartbeat_check_time < HEARTBEAT_CHECK_INTERVAL
        ):
            continue
        self.check_daemon_heartbeats()        # stale heartbeat => WARNING only
```

And the freshness grace ladder inside `check_workspace_freshness`: a failed workspace refresh only re-raises once `(nowish - last_workspace_update_time) > DEFAULT_WORKSPACE_FRESHNESS_TOLERANCE` (300s); within tolerance it logs "Still within freshness tolerance" and keeps going. On success it first clears all gRPC endpoints (`clear_all_grpc_endpoints()`) so code servers are rebuilt against the refreshed workspace.

**Flow:** every 5s check thread aliveness → every 60s refresh workspace (clearing cached user-code servers) → after a 2×heartbeat-interval startup amnesty and then every 60s, log a warning listing daemons whose heartbeats exceed tolerance ("They may be running more slowly than expected or hanging"). `_daemon_heartbeat_health` falls back to locally tracked `_last_healthy_heartbeat_times` when the storage read itself throws, so a transient DB outage doesn't mass-flip health. Shutdown (`__exit__`) sets the shared `_daemon_shutdown_event`, joins each thread with timeout=30, and logs "Thread for %s did not shut down gracefully." for stragglers.
**Invariant:** The kill-vs-warn split is deliberate: thread death is unrecoverable (generator machinery gone ⇒ restart whole process, k8s restarts it); slow/hung-but-alive daemons are surfaced via heartbeats/UI instead of being murdered. A porter who makes heartbeat staleness fatal will kill healthy-but-backlogged schedulers.
**Probe:** `integration_tests/test_suites/daemon-test-suite/test_dagster_daemon_health.py` line ~141 asserts `"Stopped dagster-daemon process due to threads no longer running"` — pins that exact kill path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "check_daemon_loop workspace freshness thread health", limit: 10 });
```

## Verdict
Adopt the 5s/60s two-tier watchdog and the thread-death-kills / heartbeat-warns split plus startup amnesty before first health judgment; adapt the workspace-refresh hook to whatever your code-loading boundary is; omit the gRPC server registry TTL plumbing if you load code in-process.
