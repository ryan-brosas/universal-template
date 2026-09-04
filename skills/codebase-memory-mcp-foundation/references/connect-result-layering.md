<!-- capsule-v2 -->
# Daemon runtime connect result — what does a caller need to know after a daemon connect attempt?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do connect statuses and HELLO statuses compose into one actionable result?

## Connect status × hello status × conflict payload
**Path/Symbol:** `src/daemon/runtime.h:207–217`.
**Signature:** `typedef struct { cbm_daemon_runtime_connect_status_t status; cbm_daemon_hello_status_t hello_status; ... } cbm_daemon_runtime_connect_result_t;`
**Data Shape:** Connect statuses cover transport-level outcomes (absent/busy/connected); hello_status refines to COMPATIBLE or a specific CONFLICT kind (version/build/protocol_abi/store_abi/feature_abi/cache_root) with the populated `cbm_daemon_conflict_t` naming both sides.

### Decisive source
```c
} cbm_daemon_runtime_connect_status_t;
    cbm_daemon_runtime_connect_status_t status;
    cbm_daemon_hello_status_t hello_status;
```
```c
/* service.h: every stateful CBM frontend for one OS account must meet at one
 * endpoint; the HELLO comparison then either admits the exact build or returns
 * an explicit conflict. */
```

**Flow:** attempt connect → transport result → if connected, HELLO decides admission → on mismatch both enums PLUS the conflict record are returned so callers can print "active build X vs requested Y, reason: store ABI".
**Invariant:** Two enums are needed because "socket exists" and "build compatible" are orthogonal; collapsing them loses the ability to auto-relaunch vs hard-fail.
**Probe:** consumed across tests/test_daemon_runtime.c; conflict population pinned in tests/test_daemon_version.c:246–316.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_daemon_runtime_connect_result_t", limit: 5 });
```

## Verdict
Adopt layered result structs (transport × policy × payload) for connection APIs; adapt enum sets; keep human-readable conflict messages in the payload, not the enum.
