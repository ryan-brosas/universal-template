<!-- capsule-v2 -->
# Workspace RPC proxy — how do you turn a 40-method trait into a wire protocol without codegen?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** How can one trait implementation serialize every operation to named JSON-RPC requests while staying in sync with the server for free?

## Generic client + method-name vocabulary
**Path/Symbol:** `crates/biome_service/src/workspace/client.rs:` `WorkspaceClient` (:28-33), `WorkspaceTransport` (:35-40), `TransportRequest` (:43-47), `request` (:89-100), blanket `impl<T> Workspace for WorkspaceClient<T>` (:107-288).
**Signature:** `fn request<P, R>(&self, method: &'static str, params: P) -> Result<R, WorkspaceError> where P: Serialize, R: DeserializeOwned`.
**Data Shape:** `TransportRequest<P> { id: u64, method: &'static str, params: P }`; ids come from an `AtomicU64` (`fetch_add(_, Ordering::Relaxed)`); the struct holds `transport: T`, `request_id: AtomicU64`, `server_info: Option<ServerInfo>`, and a LOCAL `fs: Box<dyn FsWithResolverProxy>`.

### Decisive source
```rust
fn request<P, R>(&self, method: &'static str, params: P) -> Result<R, WorkspaceError>
where
    P: Serialize,
    R: DeserializeOwned,
{
    let id = self.request_id.fetch_add(1, Ordering::Relaxed);
    let request = TransportRequest { id, method, params };
    let response = self.transport.request(request)?;
    Ok(response)
}
```

**Flow:** each `Workspace` method is ONE line — `open_project` → `"biome/open_project"`, `pull_diagnostics` → `"biome/pull_diagnostics"`, … (34 dispatch lines :111-283). The method-name string is the entire protocol; the server side switches on the same names, so the Rust type system keeps both ends aligned without IDL or codegen. Two members deliberately bypass the transport: `fs()` returns the client-local `Box<dyn FsWithResolverProxy>` directly (:222-224) — file reads never round-trip — and `server_info()` returns the value captured once at construction.
**Invariant:** every serializable operation must go through `request` so ids are unique per client and error mapping (`?` on `TransportError`) is uniform; adding a Workspace method without adding its `"biome/<name>"` line is a compile-visible diff in this impl block. `T` must be `WorkspaceTransport + RefUnwindSafe + Send + Sync`.
**Probe:** no dedicated upstream unit test drives `WorkspaceClient<T>` against a mock transport at pin (recorded caveat); the compile gate is `cargo check -p biome_service --lib` (exit 0 executed this pass) and the live counterpart is the server's method-name dispatch.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "WorkspaceClient request TransportRequest workspace client", limit: 10, fields: ["signature", "lines"] });
```
Observed GREEN retrieval at pin: `WorkspaceClient.request` Method client.rs :89-100, `TransportRequest` Struct :43-47, `WorkspaceTransport.request` :36-39 line-exact.

## Verdict
Adopt the trait-as-RPC-boundary pattern: generic transport + `'static str` method vocabulary + serde-typed params/results as a zero-codegen protocol; adapt the id allocation and the local-fs side-channel split (which operations may bypass the wire) to your host; omit Biome's specific initialize handshake ordering only if your transport has no pre-initialize restriction (see `workspace-client-initialize-bootstrap`). Coverage: client.rs `no_recorded_issue`/`generation_matches` at pin; direct source read whole (288L).
