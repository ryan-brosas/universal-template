<!-- capsule-v2 -->
# host-handshake-limits — what does the sandbox-side host enforce before any cell runs?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How does the isolated host process authenticate, bound, and isolate sessions on one connection?

## Handshake + capability gate
**Path/Symbol:** `codex-rs/code-mode-host/src/lib.rs` : `negotiate` (:281-379), constants (:57-63).
**Data Shape:** limits: 256 in-flight requests / 128 active cells (semaphore permits, try-acquire → immediate error string, never queue) / 4096 recent request+session ids / 5s shutdown timeout / 10s bulk-pairing timeout; protocol V1 only; capabilities: `dual_websocket`, `session_resource_limits`.

### Decisive source
```rust
let Ok(permit) = self.limits.request_permit() else {
    self.respond(request_id, Err("code-mode host has too many in-flight requests".to_string()));
    self.finish_request(request_id);
    return Ok(());
};
```
```rust
// open_session: session-id reuse is remembered forever-ish (LRU 4096)
if !self.seen_session_ids.lock()...remember(session_id.clone()) {
    return Err(format!("code-mode session ID `{session_id}` was reused"));
}
```

**Flow:** first message MUST be ClientHello (second hello = hard bail) → version intersection else structured `HandshakeRejected{NoCompatibleVersion}` → dual-websocket request reserves a pairing token from the registry (10s window) → required-capability check against host-advertised set → HostHello back. Requests: OpenSession/Execute/Wait/Terminate/ShutdownSession; ONLY Execute|Wait are cancellable (`RequestKind::is_cancellable`).
**Invariant:** Session-id LRU prevents a client from recycling an id to inherit a prior session's state — the id is a capability. Request-id dedupe covers active AND recent (4096-window) so late CancelRequest can't hit a recycled id. Execute over-limit responds with a data error and STILL finishes/registers the request id (no leak). Disconnect path: cancel all → close tracker → drain tasks → shutdown every session → bounded 2×5s timeouts.
**Probe:** `code-mode-host/src/host_tests.rs` at pin; robustness_tests.rs covers writer-failure propagation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "HostLimits negotiate MAX_IN_FLIGHT_REQUESTS SeenSessionIds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt semaphore-based admission with fail-fast strings, seen-session-id LRU, and cancellable-only Execute/Wait classification. Adapt constants. Omit gRPC/websocket transport details.
