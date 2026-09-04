<!-- capsule-v2 -->
# Frozen rendezvous wire frames — how do you version a handshake so old and new builds can always diagnose each other?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What frame sizes/fields must NEVER change, and how does cross-version shutdown stay parseable when HELLO would conflict?

## Fixed-layout rendezvous envelope + separate activation-shutdown first frame
**Path/Symbol:** `src/daemon/runtime.h:20–58`.
**Signature:** constants only — `CBM_DAEMON_RENDEZVOUS_REQUEST_SIZE 133`, `..._RESPONSE_SIZE 798`, `CBM_DAEMON_ACTIVATION_SHUTDOWN_REQUEST_SIZE 137`, `..._RESPONSE_SIZE 24`, `CBM_DAEMON_CONTROL_*`, `CBM_DAEMON_MAX_FRAME_SIZE 10 MiB` (daemon.h:20).
**Data Shape:** Request: u32 ABI @0, version[64] @4, build[65] @68. Response: connect @0, hello @4, client @8, PID @16, conflict @24, active/requested version+build pairs, message[512] — all network byte order. Detailed post-admission ABI deliberately EXCLUDED from the stable envelope.

### Decisive source
```c
/* Permanent account-wide rendezvous envelope, generation zero. These numeric
 * capacities and byte sizes are frozen independently of service/runtime data
 * structures. A future generation must preserve both request and response
 * layouts exactly at the stable endpoint.
 * ... Cross-version activation shutdown is a separate first-frame protocol which
 * remains parseable when normal HELLO would report a version/build conflict. */
/* [Detailed op ABI] is deliberately absent from the stable endpoint HELLO: an
 * exact executable fingerprint already selects this layout, while conflicting
 * generations must remain able to DIAGNOSE each other even when this value and
 * every detailed payload have changed. */
```

**Flow:** client encodes fixed 133-byte identity → daemon responds 798 bytes with conflict details sized for BOTH generations' strings → if versions conflict, activation shutdown (u32 action + unchanged 133-byte identity) still parses on either side → post-admission ops ride CBM_DAEMON_RUNTIME_WIRE_ABI which only exact-build peers share.
**Invariant:** The stable endpoint is frozen at generation zero; diagnostics payloads live OUTSIDE it precisely so mismatched builds can communicate about being mismatched.
**Probe:** size/layout pinned by tests/test_daemon_ipc.c and runtime contract timeouts in tests/test_daemon_runtime_contract.h.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "CBM_DAEMON_RENDEZVOUS_ABI", limit: 5 });
```

## Verdict
Adopt frozen-envelope + out-of-band detail ABI split for any protocol needing cross-version diagnosis; adapt byte budgets; never widen the stable frame — add a new one.
