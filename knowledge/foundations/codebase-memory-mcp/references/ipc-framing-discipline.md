<!-- capsule-v2 -->
# Daemon IPC framing — how do you length-prefix messages over a stream socket without partial-read bugs?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What read/write discipline handles short reads, oversize frames, and interruptible waits?

## recv_exact loop + 4-byte network-order length + cap check
**Path/Symbol:** `src/daemon/ipc.c` (framing core) + tests/test_daemon_ipc.c suite (118 tests).
**Signature:** internal `recv_exact(fd, buf, len, deadline)` looping until filled or timeout; send path symmetrical.
**Data Shape:** Every frame: u32 big-endian payload length ≤ CBM_DAEMON_MAX_FRAME_SIZE, then raw bytes; reads loop on EINTR and short counts; oversize ⇒ protocol error, connection closed.

### Decisive source
```c
/* Exact-count receive loops handle short reads and EINTR; the leading
 * network-order length is validated against the frame ceiling BEFORE any
 * allocation, so a corrupt or hostile peer cannot force an oversized buffer. */
```

**Flow:** await header → validate against cap → allocate exactly → recv_exact body → dispatch by op flag → replies mirror the same envelope.
**Invariant:** Validate-then-allocate ordering is the security property; every blocking wait must honor deadlines/interrupts for cancellation to work end-to-end.
**Probe:** tests/test_daemon_ipc.c framing/partial-read cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_daemon_ipc_frame", limit: 5 });
```

## Verdict
Adopt validate-then-allocate exact-count framing for stream protocols; adapt caps; keep EINTR loops explicit in C.
