<!-- capsule-v2 -->
# Two-map document lifecycle — how do you close and reopen a CRDT document without losing in-flight sync state or leaking memory?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** Why does DocumentManager keep TWO maps (`documents` + `removing_documents`) with a 120-second delayed eviction, and what breaks if a porter collapses them into one LRU?

## documents / removing_documents graveyard
**Path/Symbol:** `frontend/rust-lib/flowy-document/src/manager.rs:DocumentManager` (fields :57-58, `editable_document` :222-232, `open_document` :327-339, `close_document` :341-365, `restore_document_from_removing` :493-501).
**Signature:** `documents: Arc<DashMap<Uuid, Arc<RwLock<Document>>>>`; `removing_documents: Arc<DashMap<Uuid, Arc<RwLock<Document>>>>`; `async fn close_document(&self, doc_id: &Uuid) -> FlowyResult<()>`.
**Data Shape:** Both maps hold the SAME value type; a doc moves between them by `DashMap::remove` + `insert`, keeping its `Arc` (and thus its Yrs doc, subscriptions, and sync plugin) alive.

### Decisive source
```rust
// close_document (:342-361)
if let Some((doc_id, document)) = self.documents.remove(doc_id) {
  { let mut lock = document.write().await;
    lock.clean_awareness_local_state(); }          // clear MY presence before parking
  self.removing_documents.insert(doc_id, document); // park, do NOT drop
  let weak_removing_documents = Arc::downgrade(&self.removing_documents);
  tokio::spawn(async move {
    tokio::time::sleep(std::time::Duration::from_secs(120)).await;
    if let Some(removing_documents) = weak_removing_documents.upgrade() {
      if removing_documents.remove(&clone_doc_id).is_some() {
        trace!("drop document from removing_documents: {}", clone_doc_id);
      } } });
}
```
```rust
// restore (:493-501) — reopen before eviction resurrects the SAME instance
fn restore_document_from_removing(&self, doc_id: &Uuid) -> Option<Arc<RwLock<Document>>> {
  let (doc_id, doc) = self.removing_documents.remove(doc_id)?;
  self.documents.insert(doc_id, doc.clone());
  Some(doc)
}
```

**Flow:** Close: remove from active map → wipe local awareness state → insert into graveyard → spawn a 120s timer that removes the entry (the last `Arc` drop then tears the doc down). Open/get paths consult `documents` FIRST, then `restore_document_from_removing` (which re-inserts into active), and only then build a fresh instance. `open_document` on a parked doc calls `lock.start_init_sync()` on the restored instance.
**Invariant:** A closed-then-reopened document resumes as THE SAME in-memory collab (pending push updates, awareness clock, sync plugin state all survive) instead of rebuilding from disk and racing the server's view of that doc. The eviction timer holds only a Weak to the map so manager drop cancels cleanup harmlessly.
**Probe:** `/tmp/extcollab-af-probe` battery pins adjacent kernels; this seam pinned by byte-exact source read at HEAD. Direct suite blocked at this pin: `cargo test -p flowy-document` fails compiling `librocksdb-sys` C++ here (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "DocumentManager close_document removing_documents restore_document_from_removing", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-map graveyard pattern for any long-lived collaborative object with expensive reconnect semantics. Adapt the dwell time (120s is a product choice) and awareness-cleanup hook to your stack. Omit the DashMap specifics if your host single-threads access.
