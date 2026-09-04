<!-- capsule-v2 -->
# Daemon runtime client — what does the per-connection coordinator lease own?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Why do connections hold coordinator leases, and what happens to them on abrupt disconnect?

## Connection-owned leases released on disconnect
**Path/Symbol:** `src/daemon/runtime.h:5` (layer contract) + `cbm_daemon_runtime_client_t` (103) + drain snapshots in STOP protocol.
**Signature:** connect returns a client handle bundling connection + coordinator leases; close drains.
**Data Shape:** The layer "combines authenticated local IPC transport, exact-build HELLO policy, and connection-owned coordinator leases" and deliberately does NOT spawn daemons — bootstrap is a caller concern.

### Decisive source
```c
/* runtime.h — Mandatory per-account CBM daemon runtime.
 * This layer combines the authenticated local IPC transport, exact-build
 * HELLO policy, and connection-owned coordinator leases. It deliberately
 * does not spawn the daemon process; executable bootstrap is a caller concern. */
```

**Flow:** caller bootstraps executable → opens runtime client (transport+HELLO+lease bundle) → operations ride frames → on close/disconnect the connection's coordinator leases release so project mutation locks don't leak to dead peers.
**Invariant:** Layering rule: transport/policy/leases together; process spawning apart — keeps the runtime testable without exec.
**Probe:** tests/test_daemon_runtime.c suite (118 tests) incl. pending-wait race trio.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_daemon_runtime_client_t", limit: 5 });
```

## Verdict
Adopt lease-bundled connection handles with spawn-free layering; adapt to your lock registry; the "bootstrap is a caller concern" split is the reusable architecture.
