<!-- capsule-v2 -->
# Stdio buffering hang — why does mixing FILE* getline with poll() block your server for 60s?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the classic libc-buffer-vs-poll interaction bug in stdio servers, and how is it caught?

## Rapid-message test with alarm(5) watchdog
**Path/Symbol:** `src/mcp/mcp.c:cbm_mcp_server_run` + tests/test_mcp.c:8588 (`mcp_server_run_rapid_messages`).
**Signature:** `int cbm_mcp_server_run(cbm_mcp_server_t *srv, FILE *in, FILE *out);`
**Data Shape:** Client sends initialize + notification + tools/list in ONE write. Bug class: first getline() over-reads kernel bytes into the libc buffer; a subsequent poll() on the FD sees no data (it's in userspace!) and blocks 60s. The fix drains buffered lines before polling.

### Decisive source
```c
/* Simulate a client sending initialize + notifications/initialized +
 * tools/list all at once (no delays), which exercises the FILE*
 * buffering fix: the first getline() over-reads kernel data into the
 * libc buffer; without the fix, subsequent poll() calls block for 60s.
 * We use alarm(5) to abort the test process if the server hangs. */
```

**Flow:** pipe with all messages at once → run server under alarm → both responses must appear before EOF handling.
**Invariant:** Never mix readiness syscalls with stdio buffering without draining; watchdog alarms turn hangs into test failures instead of CI timeouts.
**Probe:** `tests/test_mcp.c:mcp_server_run_rapid_messages`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "server_run", limit: 5 });
```

## Verdict
Adopt rapid-burst tests with alarm watchdogs for any stdio loop; adapt framing; this bug recurs in every language with buffered stdin.
