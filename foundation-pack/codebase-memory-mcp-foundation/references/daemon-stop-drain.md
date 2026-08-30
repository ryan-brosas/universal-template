<!-- capsule-v2 -->
# Daemon stop/drain protocol — how do you shut down a shared daemon when some clients are mid-request?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does the STOP wire contract guarantee about committed clients and drained connections?

## Fixed-size control frames + committed-client snapshot excluding requester
**Path/Symbol:** `src/daemon/runtime.h:50–58` (STATUS/STOP sizes, `CBM_DAEMON_CONTROL_CLIENT_CAP 8`) + runtime.c drain semantics; tests/test_daemon_runtime.c:500–530 pending-timeout/cancel races.
**Signature:** STOP request = 65 bytes (claimed build fingerprint, kernel-peer-verified); response = 40 bytes with capped pid table.
**Data Shape:** Responses carry u64 active-client and drained-connection snapshots; the ACTIVATION REQUESTER excludes itself from drained counts. Requests carry only the claimed fingerprint — the kernel-verified peer identity is cross-build by design.

### Decisive source
```c
/* STATUS/STOP wire sizes. Requests carry only the requester's claimed build
 * fingerprint (kernel-peer-verified, cross-build by design). Responses are
 * fixed-size with a capped committed-client pid table. */
#define CBM_DAEMON_CONTROL_REQUEST_SIZE 65U
#define CBM_DAEMON_STOP_RESPONSE_SIZE 40U
/* ... u64 active client snapshot @8, u64 drained-connection snapshot @16
 * (the activation requester excludes itself). */
```

**Flow:** maintenance client sends STOP with its fingerprint → daemon verifies via SO_PEERCRED-class kernel identity → quiesce callback requests orderly draining → response reports how many clients were active vs drained (excluding requester) → bounded waits with timeout-race handling so a connection completing during drain is never lost (`pending_timeout_race_returns_completed_io`).
**Invariant:** Drain snapshots must exclude the requester or operators misread liveness; fixed-size responses keep cross-version parsing possible even at conflict.
**Probe:** `tests/test_daemon_runtime.c:daemon_ipc_pending_timeout_race_returns_completed_io`, `daemon_ipc_pending_wait_failure_cancels_and_drains`, plus cohort mutation-wait family in tests/test_version_cohort.c:394–443.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "drain", limit: 5 });
```

## Verdict
Adopt peer-verified control frames with self-excluding snapshots for coordinated shutdowns; adapt caps; keep cross-build parseability — that's why fingerprints ride in clear.
