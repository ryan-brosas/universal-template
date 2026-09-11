<!-- capsule-v2 -->
# Collab builder lifecycle — how do you assemble a local-first CRDT object with disk persistence and cloud sync without double-initializing plugins?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** What is the exact construction order for a `Collab`-backed object (document/folder/awareness/database), and which steps are load-bearing so a port does not lose data or re-add sync plugins?

## Builder lifecycle: build → domain-open → finalize
**Path/Symbol:** `frontend/rust-lib/collab-integrate/src/collab_builder.rs:AppFlowyCollabBuilder` (`build_collab` :274-302, `create_document` :158-193, `finalize` :304-359, `write_collab_to_disk` :363-397).
**Signature:** `async fn build_collab(&self, object: &CollabObject, collab_db: &Weak<CollabKVDB>, data_source: DataSource) -> Result<Collab, Error>`; `fn finalize<T: BorrowMut<Collab>+Send+Sync+'static>(&self, object, build_config, collab: Arc<RwLock<T>>) -> Result<Arc<RwLock<T>>, Error>`.
**Data Shape:** `CollabObject{uid:i64, object_id:String, collab_type, workspace_id:String, device_id}`; `collab_db` is a Weak — the KV store is owned by the user session, not the builder.

### Decisive source
```rust
// build_collab (:283-299) — CRDT construction must leave the async thread pool
let collab = tokio::task::spawn_blocking(move || {
  let collab = CollabBuilder::new(object.uid, &object.object_id, data_source)
    .with_device_id(device_id)
    .build()?;
  let db_plugin = RocksdbDiskPlugin::new_with_config(
    object.uid, object.workspace_id.clone(), object.object_id.to_string(),
    object.collab_type, collab_db, CollabPersistenceConfig::default());
  collab.add_plugin(Box::new(db_plugin));
  Ok::<_, Error>(collab)
}).await??;
```
```rust
// finalize (:324-356) — plugin attach happens while the collab is still unexposed
let mut write_collab = collab.try_write()?;
if write_collab.borrow().has_cloud_plugin() { drop(write_collab); return Ok(collab); }
if build_config.sync_enable {
  let plugins = plugin_provider.get_plugins(CollabPluginProviderContext::AppFlowyCloud { .. });
  // at the moment when we get the lock, the collab object is not yet exposed outside
  for plugin in plugins { write_collab.borrow().add_plugin(plugin); }
}
(*write_collab).borrow_mut().initialize();
```

**Flow:** (1) `collab_object()` validates the caller's workspace_id against the CURRENT open workspace (`:135-142` — mismatch is an error because async callers may race a workspace switch); (2) `build_collab` constructs the Yrs doc inside `spawn_blocking`, attaching the RocksDB persistence plugin BEFORE any data loads; (3) domain wrapper opens or creates (`Document::open` vs `create_with_data`; created docs are immediately flushed via `write_collab_to_disk`, which encodes with `collab_type.validate_require_data` and `flush_doc(state_vector, doc_state)` + explicit `commit_transaction`); (4) `finalize` queues embedding work as a spawned task holding only Weak refs, then takes a write lock, checks `has_cloud_plugin()` for idempotence, attaches cloud-sync plugins exactly once, and calls `initialize()` to start sync.
**Invariant:** Cloud plugins attach AT MOST ONCE per collab instance (the `has_cloud_plugin()` early-return is the guard); the write lock in `finalize` is held across plugin attachment precisely because "the collab object is not yet exposed outside" — no observer can see a half-wired doc. Domain creation writes to disk BEFORE returning (a crash after create leaves a valid encoded collab).
**Probe:** `/tmp/extcollab-af-probe` battery t01-t05 pin dispatch behavior of the same crate family; source pins above verified byte-exact at HEAD. Direct suite: `cargo test -p lib-dispatch` (1 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "finalize AppFlowyCollabBuilder", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-stage order (validate-workspace → blocking-build-with-persistence-plugin → flush-on-create → finalize-once-under-lock); adopt `spawn_blocking` for all Yrs encode/decode work. Adapt the plugin provider trait boundary to your host's sync backend. Omit the RocksDB-specific backup hooks and wasm IndexedDB branches unless targeting those platforms.
