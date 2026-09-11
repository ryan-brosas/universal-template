<!-- capsule-v2 -->
# Daemon IPC endpoint probe — how do you distinguish "no daemon" from "daemon busy" without races?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does a connect attempt mean on each errno, and why is ECONNREFUSED treated as ACTIVE?

## Probe = connect with timeout; refused ⇒ fail-closed ACTIVE
**Path/Symbol:** `src/daemon/ipc.c:cbm_daemon_ipc_endpoint_probe` + header contract (ipc.h:100–131).
**Signature:** `cbm_daemon_probe_status_t cbm_daemon_ipc_endpoint_probe(endpoint, timeout_ms);`
**Data Shape:** ABSENT (ENOENT/addr-in-use-free socket file missing), ACTIVE (connect succeeded OR secure-but-refused — BSD may report ECONNREFUSED for an alive-but-busy peer), ERROR otherwise. Callers must treat ambiguity as ACTIVE.

### Decisive source
```c
/* ... secure but refused Unix socket also fails closed as active because BSD
 * may [report ECONNREFUSED for an alive-but-busy peer] */
```

**Flow:** stat endpoint → missing ⇒ ABSENT → connect non-blocking with deadline → success ⇒ ACTIVE; refusal ⇒ ACTIVE (fail closed) → other errors ⇒ ERROR. Bootstrap uses this to decide spawn vs reuse.
**Invariant:** Fail-closed on ambiguity prevents double-daemons, which are worse than a spurious "busy".
**Probe:** tests/test_daemon_ipc.c probe cases; bootstrap consumption in role routing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_daemon_ipc_endpoint_probe", limit: 5 });
```

## Verdict
Adopt fail-closed liveness probes for shared endpoints; adapt errno mapping per platform; document the BSD quirk in the API contract.
