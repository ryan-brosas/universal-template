<!-- capsule-v2 -->
# Cloud-first open fallback — when a document is missing locally, how do you fetch its initial state without creating a divergent empty doc?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** What is the exact decision ladder for opening a document that exists on another device, and why must the remote doc_state be rejected when empty?

## create_document_instance: disk → cloud → RecordNotFound
**Path/Symbol:** `frontend/rust-lib/flowy-document/src/manager.rs:DocumentManager.create_document_instance` (:238-298) + `doc_state_from_document_data` (:504-525).
**Signature:** `async fn create_document_instance(&self, doc_id: &Uuid, enable_sync: bool) -> FlowyResult<Arc<RwLock<Document>>>`.
**Data Shape:** Local path: `DataSource::Disk(Some(Box<CollabPersistenceImpl>))` (lazy — loads only if rows exist); cloud path: `DataSource::DocStateV1(Vec<u8>)` (eager bytes).

### Decisive source
```rust
// :244-266 — the fallback ladder
let mut doc_state = self.persistence()?.into_data_source();
if !self.is_doc_exist(doc_id).await? {
  info!("document {} not found in local disk, try to get the doc state from the cloud", doc_id);
  doc_state = DataSource::DocStateV1(
    self.cloud_service.get_document_doc_state(doc_id, &self.user_service.workspace_id()?).await?);
  // the doc_state should not be empty if remote return the doc state without error.
  if doc_state.is_empty() {
    return Err(FlowyError::new(ErrorCode::RecordNotFound,
      format!("document {} not found", doc_id)));
  }
}
```
```rust
// :277-297 — invalid data is DELETED, and sync-gated caching
Err(err) => { if err.is_invalid_data() { self.delete_document(doc_id).await?; } return Err(err); }
// ...only push the document to the cache if the sync is enabled:
if enable_sync { subscribe_document_changed(...); self.documents.insert(*doc_id, document.clone()); }
```

**Flow:** (1) If local KV lacks the object, fetch raw doc_state from cloud; an EMPTY success response means "no such document server-side" → `RecordNotFound`, never a blank page. (2) Build via collab builder with `sync_enable=enable_sync`. (3) On `is_invalid_data()` errors the corrupt local copy is DELETED before surfacing the error. (4) Subscriptions + cache insertion happen ONLY for sync-enabled opens (`get_document` uses `enable_sync=false`, so background reads never wire notifications or appear in `documents`). Creation is symmetric: `create_document` encodes default/user data in `spawn_blocking`, saves to disk FIRST, then spawns a detached task pushing the encoded collab to cloud.
**Invariant:** An empty remote doc_state is an ERROR, not an empty document; local-disk existence always wins over cloud (offline-first); non-sync instances are invisible to the cache and notification plumbing by construction.
**Probe:** `/tmp/extcollab-af-probe` t01-t10 (adjacent kernels); this seam pinned byte-exact at HEAD. Upstream suite blocked here: `librocksdb-sys` C++ build failure (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "create_document_instance DataSource DocStateV1 get_document_doc_state", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder (local-first, cloud-fallback, empty-remote-is-404, delete-corrupt-on-invalid-data, cache-only-syncing-instances). Adapt the cloud service trait shape. Omit reminder actions stubs (`handle_reminder_action` is a no-op match at this pin).
