<!-- capsule-v2 -->
# grpc-session-provider — when is the gRPC transport used and what does it change?

**Source:** open-interpreter Apache-2.0 `main@5b07159c477920c159d8892d112b480e7307f257`; Codebase Memory `ext-open-interpreter`. **Question:** What does the second session-provider family (gRPC) add over process/WebSocket, and which invariants are shared?

## GrpcCodeModeSessionProvider + GrpcCodeModeHost
**Path/Symbol:** `codex-rs/code-mode/src/grpc_session/mod.rs` (:1-349); host twin `code-mode-host/src/grpc/` (`GrpcCodeModeHost`, routing/session/events/transport/conversions).
**Data Shape:** same `CodeModeSessionProvider` trait; state tests (521L) + operations (421L) mirror the stdio driver's command set; host side routes gRPC calls onto the SAME `HostState::handle_request`.

### Decisive source
```rust
// code-mode/src/lib.rs — three providers, one trait:
pub use grpc_session::GrpcCodeModeSessionProvider;
pub use remote_session::DisabledCodeModeSessionProvider;
pub use remote_session::ProcessOwnedCodeModeSession;
pub use remote_session::ProcessOwnedCodeModeSessionProvider;
pub use remote_session::WebSocketCodeModeSessionProvider;
```

**Flow:** transport choice is a provider detail; the session/runtime/cell stack (protocol types → InProcessCodeModeSession → cell actors → V8) is IDENTICAL across stdio, WebSocket, and gRPC. The host gRPC module reuses HostState so limits, seen-session LRU, and request dedupe apply unchanged.
**Invariant:** Because all transports converge on one handle_request, behavioral fixes at the host apply to every transport; porters must not fork per-transport semantics. The disabled provider exists as an explicit fail-closed object (`availability: Err("code-mode host is disabled")`) so config can turn code mode off without null checks.
**Probe:** `grpc_session/state_tests.rs` + `code-mode-host/src/grpc/service_tests.rs` + robustness_tests.rs at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-interpreter", query: "GrpcCodeModeSessionProvider GrpcCodeModeHost", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-trait/multi-transport convergence on one host handler. Omit proto codec specifics. Coverage caveat: this capsule maps the composition seam; deep per-file mining of grpc_session/* is queued for pass 2.
