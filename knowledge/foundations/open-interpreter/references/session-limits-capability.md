<!-- capsule-v2 -->
# session-limits-capability — how are per-session resource limits negotiated without breaking old hosts?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** How does `create_session_with_limits` stay backward-compatible across protocol versions?

## Default-degrade provider default
**Path/Symbol:** `codex-rs/code-mode-protocol/src/session.rs` : `CodeModeSessionProvider::create_session_with_limits` (:183-195); `code-mode/src/remote_session/connection.rs` : capability gate (:495-504); host lib.rs : OpenSession limits conversion (:448-455).
**Data Shape:** `CodeModeSessionCellExecutionLimits { max_yield_time_ms: Option<u64>, max_heap_size_bytes: Option<usize> }`; default = both None.

### Decisive source
```rust
fn create_session_with_limits<'a>(&'a self, delegate: ..., limits: ...) -> ... {
    if limits == CodeModeSessionCellExecutionLimits::default() {
        self.create_session(delegate)                    // old providers keep working
    } else {
        Box::pin(async { Err("code-mode session provider does not support resource limits".to_string()) })
    }
}
```
```rust
// client side, per connection:
if limits != Default::default() && !self.capabilities.iter().any(|c| c.as_str() == SESSION_RESOURCE_LIMITS_CAPABILITY) {
    return Err(format!("code-mode host does not support session resource limits: missing `{SESSION_RESOURCE_LIMITS_CAPABILITY}` capability"));
}
```

**Flow:** trait default degrades ONLY when the requested limits are the default (zero-cost compat) → non-default limits require the peer to have ADVERTISED `session_resource_limits` during handshake → host converts wire limits via `TryFrom` with loud validation errors before creating the InProcessCodeModeSession. Note: in-process sessions FORCE heap limit to None (`with_delegate_and_limits` overwrites it) — only yield clamping is honored locally today.
**Invariant:** The capability is negotiated, never assumed: a client that skips the check against an older host would silently run unclamped cells. Heap size is plumbed through the protocol but intentionally not enforced by the in-process runtime — porting "max_heap_size_bytes works" without a real enforcement point would be a fabricated guarantee.
**Probe:** host_tests + remote_session_tests at pin; service.rs constructor shows the deliberate None-overwrite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "create_session_with_limits SESSION_RESOURCE_LIMITS_CAPABILITY", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt default-only degrade plus explicit capability gating; adopt honest non-enforcement of heap limits. Omit wire struct details.
