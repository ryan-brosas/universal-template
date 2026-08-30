<!-- capsule-v2 -->
# Daemon runtime client — how do you connect, HELLO-handshake, and keep a control connection alive for days?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What wait semantics let an idle authenticated session survive indefinitely without dropping?

## WAIT_FOREVER sentinel + interruptible-by-EOF waits
**Path/Symbol:** `src/daemon/runtime.h:24–31` + `src/daemon/runtime.c` connect/HELLO flow; tests/test_daemon_runtime.c pending-wait trio (500–530).
**Signature:** `#define CBM_DAEMON_IPC_WAIT_FOREVER UINT32_MAX` + `cbm_daemon_runtime_connect(endpoint, identity, timeout_ms, result)`.
**Data Shape:** Connect performs u32 connect + u32 hello exchange over the rendezvous envelope (see frozen-wire capsule); receives may specify WAIT_FOREVER which remains interruptible by peer EOF and `cbm_daemon_ipc_connection_interrupt()`.

### Decisive source
```c
/* A receive wait with no wall-clock expiry. The wait remains interruptible by
 * peer EOF and cbm_daemon_ipc_connection_interrupt(). This is intentionally a
 * named sentinel rather than a very large finite timeout: authenticated MCP
 * sessions routinely remain idle for days, and a long-running application
 * request must not lose its control connection merely because no new frame is
 * arriving. */
#define CBM_DAEMON_IPC_WAIT_FOREVER UINT32_MAX
```

**Flow:** resolve endpoint → connect with bounded handshake timeout → send 133-byte identity → validate 798-byte response (conflict ⇒ populated record, see version-cohort capsule) → enter request loop where idle receives use WAIT_FOREVER but every wait is cancellable via connection-interrupt or peer close.
**Invariant:** Idle-for-days must not require traffic-based keepalives; interruption must be explicit API surface so cancellation can reach a blocked receive.
**Probe:** `tests/test_daemon_runtime.c:daemon_ipc_pending_timeout_race_returns_completed_io`, `daemon_ipc_pending_wait_failure_cancels_and_drains`, `daemon_ipc_pending_timeout_cancelled_returns_timeout`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_daemon_ipc_connection_interrupt", limit: 5 });
```

## Verdict
Adopt named infinite-wait sentinels with explicit interrupt handles for control channels; adapt to your transport; pair with the frozen envelope for cross-version safety.
