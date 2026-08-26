<!-- capsule-v2 -->
# Sync kill-switch — how do you disable cloud sync at runtime without tearing down managers?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** What happens when a cloud service is asked for data while sync is disabled, and where exactly is the gate enforced?

## AFServerImpl: Option<Arc<Client>> as the gate
**Path/Symbol:** `frontend/rust-lib/flowy-server/src/af_cloud/server.rs:AFServerImpl` (:387-409) + `get_server_impl` (:113-121) + `set_enable_sync` (:166-169).
**Signature:** `fn get_client(&self) -> Option<Arc<AFCloudClient>>`; `fn try_get_client(&self) -> Result<Arc<AFCloudClient>, Error>`; `fn set_enable_sync(&self, uid: i64, enable: bool)` storing into `Arc<AtomicBool>` (SeqCst).
**Data Shape:** Every cloud impl struct holds `inner: AFServerImpl { client: Option<...> }` — the OPTION is resolved at each SERVICE-ACCESSOR call, not stored per operation.

### Decisive source
```rust
// :113-120 — the gate snapshots the AtomicBool when services are handed out
fn get_server_impl(&self) -> AFServerImpl {
  let client = if self.enable_sync.load(Ordering::SeqCst) { Some(self.client.clone()) } else { None };
  AFServerImpl { client }
}
```
```rust
// :397-405 — disabled sync = typed error, never a hang or silent empty
None => Err(FlowyError::new(
  ErrorCode::DataSyncRequired,
  "Data Sync is disabled, please enable it first").into()),
```

**Flow:** `set_enable_sync(false)` flips an atomic; the next `user_service()/document_service()/...` call bakes `None` into the impl; every downstream operation hits `try_get_client` → `DataSyncRequired`. The same AtomicBool gates websocket reconnection in `spawn_ws_conn` (no reconnect attempts while disabled). Network reachability has its own atomic (`set_network_reachable`) consumed by collab plugins rather than this gate.
**Invariant:** Disabling sync never blocks or drops queued work — it makes NEW server access fail fast with a typed, user-visible error while local-first reads/writes continue untouched. Because the flag is sampled at accessor time, already-dispatched operations finish against their captured client.
**Probe:** Source-pinned byte-exact at HEAD (`AFServerImpl` :387-409, `get_server_impl` :113-121). Retrieval line-exact via "spawn_ws_conn TokenState Refresh Invalid disconnect" (same file) and "attempt_reconnect" rank#1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "AFServerImpl try_get_client DataSyncRequired enable_sync", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt option-typed client access with a typed DataSyncRequired-style error and accessor-time sampling. Adapt flag storage to your config system. Omit the reachability twin if your plugins handle it internally.
