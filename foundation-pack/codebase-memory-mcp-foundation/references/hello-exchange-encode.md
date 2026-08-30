<!-- capsule-v2 -->
# Daemon runtime connect — what is the exact HELLO exchange a client performs before any tool call?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do encode/decode of the rendezvous frames compose into connect, and what does each response field mean to the caller?

## Encode identity → send 133B → decode 798B → branch on (connect, hello)
**Path/Symbol:** `src/daemon/runtime.c` — `cbm_daemon_runtime_hello_request_encode` (224) + connect result struct (207–217).
**Signature:** `bool cbm_daemon_runtime_hello_request_encode(uint8_t out[CBM_DAEMON_RENDEZVOUS_REQUEST_SIZE], const cbm_daemon_build_identity_t *identity);`
**Data Shape:** Request: network-order u32 ABI + version[64] + build[65] (NUL-padded). Response decoded into {connect_status, hello_status, client handle, pid, conflict{active/requested version+build, message[512]}}.

### Decisive source
```c
/* Response: u32 connect @0, u32 hello @4, u64 client @8, u64 PID @16,
 * u32 conflict @24, active version[64] @28, active build[65] @92,
 * requested version[64] @157, requested build[65] @221,
 * message[512] @286. All integers use network byte order. */
```

**Flow:** fill identity (semantic_version, executable fingerprint, cache fingerprint, ABIs) → strict encode into the fixed frame → transport send/recv → validate sizes → decode → OK ⇒ proceed; CONFLICT ⇒ surface both builds' strings from the message region; BUSY/absent ⇒ retry policy at caller.
**Invariant:** Encode must NUL-pad exactly; decoders must accept only exact frame sizes — leniency here defeats the frozen-envelope cross-version guarantees.
**Probe:** exercised throughout tests/test_daemon_runtime.c and tests/test_daemon_ipc.c generation-address tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "hello_request_encode", limit: 5 });
```

## Verdict
Adopt fixed-frame strict encoders for stable handshakes; adapt field budgets; keep byte-order and padding rules in ONE encoder function.
