<!-- capsule-v2 -->
# Client initialize bootstrap — what must happen before a remote workspace accepts any request?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** Where should the protocol handshake live so callers can never fire a request into an uninitialized server?

## Constructor-gated handshake + consuming shutdown
**Path/Symbol:** `crates/biome_service/src/workspace/client.rs:` `new` (:61-87), `InitializeResult` (:51-55), `shutdown` (:102-104).
**Signature:** `pub fn new(transport: T, fs: Box<dyn FsWithResolverProxy>) -> Result<Self, WorkspaceError> where T: WorkspaceTransport + RefUnwindSafe + Send + Sync`.
**Data Shape:** handshake sends `json!({"capabilities": {}, "clientInfo": {"name": env!("CARGO_PKG_NAME"), "version": biome_configuration::VERSION}})` and stores the returned `server_info` in the client; `shutdown()` takes `self` by value and sends unit (`()`) params.

### Decisive source
```rust
// TODO: The current implementation of the JSON-RPC protocol in
// tower_lsp doesn't allow any request to be sent before a call to
// initialize, this is something we could be able to lift by using our
// own RPC protocol implementation
let value: InitializeResult = client.request("initialize", json!({ ... }))?;
client.server_info = value.server_info;
```

**Flow:** construct with zeroed id counter → MANDATORY `"initialize"` round-trip inside the constructor → capture `ServerInfo` → only then is the client returned, so no caller can obtain a handle that skips the handshake. Termination mirrors it: `shutdown(self)` consumes ownership, making post-shutdown use of that client unrepresentable.
**Invariant:** the constructor is fallible and returns `WorkspaceError` — a failed handshake means NO client exists, not a client in a bad state. The raw `json!` payload (not a typed params struct) is deliberate: this request speaks the transport's LSP-flavored dialect, not the workspace's typed one.
**Probe:** `cargo check -p biome_service --lib` exit 0 (executed at pin); upstream has no unit test for the handshake path (recorded caveat) — behavior is pinned downstream by the daemon CLI flow that calls `open_transport` then constructs the client.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "initialize ServerInfo InitializeResult shutdown client", limit: 10, fields: ["signature", "lines"] });
```
Observed GREEN retrieval at pin (re-executed pass 18): `InitializeResult` Struct client.rs :51-55, `WorkspaceClient.shutdown` :102-104, and the `WorkspaceClient.new` cluster resolve line-exact.

## Verdict
Adopt constructor-fallible handshake + consuming shutdown as the lifecycle pair; adapt the exact capability payload/version stamp to your protocol; omit the tower-lsp-specific constraint comment once your transport lifts it (the TODO shows upstream considers it incidental, not essential). Coverage: `no_recorded_issue` at pin; source read whole.
