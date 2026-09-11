<!-- capsule-v2 -->
# code-mode-crate-topology — how do the four code-mode crates split responsibilities?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** Where does a porter put new behavior: protocol, runtime, host, or core integration?

## Dependency and ownership map
**Path/Symbol:** `codex-rs/code-mode/src/lib.rs`, `code-mode-protocol/src/lib.rs`, `code-mode-runtime/src/lib.rs`, `code-mode-host/src/lib.rs` (module trees); `core/src/tools/code_mode/` (consumer).
**Data Shape:** protocol (types + description rendering + wire) ← runtime (V8 engine, cell actors, in-process sessions) ← host (process boundary: handshake, limits, transports) ← code-mode crate (client-side providers: process-owned/websocket/grpc/disabled) ← core `tools/code_mode` (turn integration: handlers, broker, output framing).

### Decisive source
```rust
// code-mode-protocol re-exports are the shared vocabulary everywhere else:
pub use session::CodeModeSession;          // trait
pub use session::CodeModeSessionProvider;  // trait
pub use runtime::ExecuteRequest;
// host runs InProcessCodeModeSession from the runtime:
use codex_code_mode_runtime::InProcessCodeModeSession;
```

**Flow (one exec):** model call → core handler (parse, gather tools) → provider.create_session → transport → host handle_request → InProcessCodeModeSession.execute → SessionRuntime.start_cell → CellActor → spawn_runtime (V8 thread) → events back → cell actor observe modes → RuntimeResponse → handler frames output.
**Invariant:** Domain types live ONLY in protocol; runtime/host/core never redefine CellId or RuntimeResponse — they convert via TryFrom/newtype mirrors at boundaries. The V8 feature flag (`v8-runtime`) is contained entirely inside code-mode-runtime; without it every execute returns a rebuild-instruction error string instead of failing to link.
**Probe:** crate graph resolvable via search_graph cross-crate traces; lib.rs module lists at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "CodeModeSessionProvider InProcessCodeModeSession codex_code_mode_protocol", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-layer split with single-source domain types. Adapt layer names. Omit workspace build specifics.
