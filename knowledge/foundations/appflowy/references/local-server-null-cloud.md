<!-- capsule-v2 -->
# Local-server null-object ladder — how does a fully-offline app satisfy every cloud trait without a server?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** When there is no backend, which cloud operations are answered from the local KV store, which return empty-success, and which must fail loudly?

## LocalServer: same AppFlowyServer trait, local answers
**Path/Symbol:** `frontend/rust-lib/flowy-server/src/local_server/server.rs:LocalServer` (:22-109) + `impls/folder.rs:get_folder_doc_state` (:42-70) + `util.rs:default_encode_collab_for_collab_type` (:11-47).
**Signature:** `async fn get_folder_doc_state(&self, workspace_id: &Uuid, uid: i64, collab_type: CollabType, object_id: &Uuid) -> Result<Vec<u8>, FlowyError>`; `pub async fn default_encode_collab_for_collab_type(_uid: i64, object_id: &str, collab_type: CollabType) -> FlowyResult<EncodedCollab>`.
**Data Shape:** The offline host implements the SAME `AppFlowyServer` trait as AppFlowyCloudServer; each accessor returns a fresh impl struct (no shared client); `file_storage()` returns `None`, `database_ai_service()` `None`.

### Decisive source
```rust
// folder.rs :50-70 — "cloud" read is answered FROM THE LOCAL KV STORE
let collab_db = self.logged_user.get_collab_db(uid)?.upgrade().unwrap();
let read_txn = collab_db.read_txn();
if read_txn.is_exist(uid, &workspace_id, &object_id) {
  let collab = Collab::new_with_origin(CollabOrigin::Empty, &object_id, vec![], false);
  read_txn.load_doc(uid, &workspace_id, &object_id, collab.doc())?;
  let data = collab.encode_collab_v1(|c| collab_type.validate_require_data(c) ...)?;
  Ok(data.doc_state.to_vec())
} else {
  let data = default_encode_collab_for_collab_type(uid, &object_id, collab_type).await?;
  Ok(data.doc_state.to_vec())
}
```
```rust
// util.rs :35-38 — some defaults MUST fail loudly instead of inventing data
CollabType::Folder => Err(FlowyError::not_support()
  .with_context("Can not create default folder")),
```

**Flow:** Offline bootstrap replays the sync protocol locally: `get_folder_doc_state` reads the KV store and re-encodes to doc_state; missing objects get per-type defaults (document/database/workspace-database/awareness have constructors; Folder and DatabaseRow REFUSE with `not_support`). Publish APIs fail (`local_version_not_support`), unpublish is silent-Ok, snapshots return empty vecs, and `full_sync_collab_object` routes into the local embedding writer so search indexing still works without any server.
**Invariant:** The offline mode is NOT a stub layer — it answers the exact wire-shaped queries the sync engine would ask a server, so the SAME client sync code runs unchanged; only operations that genuinely require multi-user infrastructure fail, and they fail with typed errors rather than empty successes.
**Probe:** `/tmp/extcollab-af-probe` battery pins adjacent kernels; this seam pinned byte-exact at HEAD (`get_folder_doc_state`, `default_encode_collab_for_collab_type`). Adversarial retrieval on ext-meetily for this symbol family: total:0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "LocalServer AppFlowyServer LocalServerFolderCloudServiceImpl get_folder_doc_state", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "implement the cloud trait against your local store" as THE offline-first pattern. Adapt which types have safe defaults. Omit publish/shared-user surfaces unless porting them too.
