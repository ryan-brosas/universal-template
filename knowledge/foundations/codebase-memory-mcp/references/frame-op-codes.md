<!-- capsule-v2 -->
# Daemon runtime frame ops — how do you multiplex request/response/cancel over one authenticated socket?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What frame-flag grammar and payload cap keep the daemon wire extensible but bounded?

## Op-code flags + 10 MiB frame ceiling − 16-byte header
**Path/Symbol:** `src/daemon/runtime.h:60–99` (frame flags) + `CBM_DAEMON_RUNTIME_APPLICATION_PAYLOAD_MAX` (58) ← `CBM_DAEMON_MAX_FRAME_SIZE 10U*1024U*1024U` (daemon.h:20).
**Signature:** "Frame flags are operation codes. Every operation has one exact payload [layout]" — request, response chunk, cancel notice, etc.
**Data Shape:** Application payload capped at MAX_FRAME_SIZE−16 (header); connection state tracks active_connections with a hard cap on accepted connection THREADS including not-yet-identified sockets; last-committed-client disconnect triggers drain semantics.

### Decisive source
```c
/* Frame flags are operation codes. Every operation has one exact payload ... */
#define CBM_DAEMON_RUNTIME_APPLICATION_PAYLOAD_MAX (CBM_DAEMON_MAX_FRAME_SIZE - 16U)
...
/* Hard cap on accepted connection threads, including sockets that have not
 * been identified ... */
/* ... only the stop/drain ops or an [active-client-zero transition] ... */
```

**Flow:** accept (thread-cap gated) → identify via HELLO → frames carry op-code flag + bounded payload → cancel notices ride as first-class ops → oversized application payloads rejected at framing, before dispatch.
**Invariant:** One op = one exact layout keeps parsing total; the thread cap counts UNIDENTIFIED sockets too or a pre-HELLO flood exhausts threads.
**Probe:** tests/test_daemon_ipc.c framing suite; capacity behavior in tests/test_daemon_frontend.c:1391.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "frame", limit: 5 });
```

## Verdict
Adopt exact-layout op-code framing with header-inclusive caps for binary RPC; adapt sizes; count unidentified connections in your admission caps.
