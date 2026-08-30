<!-- capsule-v2 -->
# Disk persistence contract — how does a CRDT doc load from and flush to the local KV store without losing updates?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** What is the exact read/write protocol between a `Collab` and the on-disk update log, and what breaks if a porter commits transactions or encodes in the wrong order?

## CollabPersistenceImpl: load-into-txn, flush-state-vector
**Path/Symbol:** `frontend/rust-lib/collab-integrate/src/collab_builder.rs:CollabPersistenceImpl` (`load_collab_from_disk` :438-466, `save_collab_to_disk` :468-493, `into_data_source` :432-435).
**Signature:** `fn load_collab_from_disk(&self, collab: &mut Collab) -> Result<(), CollabError>`; `fn save_collab_to_disk(&self, object_id: &str, encoded_collab: EncodedCollab) -> Result<(), CollabError>`.
**Data Shape:** `EncodedCollab{state_vector: Bytes, doc_state: Bytes}` — disk stores (sv, doc_state) pairs, NOT raw updates; db handles are `Weak<CollabKVDB>` upgraded on demand with an explicit `"collab_db is dropped"` error.

### Decisive source
```rust
// load (:445-464) — apply stored updates INSIDE one txn, commit AFTER the read txn drops
if rocksdb_read.is_exist(self.uid, &workspace_id, &object_id) {
  let mut txn = collab.transact_mut();
  match rocksdb_read.load_doc_with_txn(self.uid, &workspace_id, &object_id, &mut txn) {
    Ok(update_count) => trace!("did load collab:{} ... update_count:{}", ...),
    Err(err) => error!("🔴 load doc:{} failed: {}", object_id, err),
  }
  drop(rocksdb_read);
  txn.commit();
}
```
```rust
// save (:478-492) — flush_doc then EXPLICIT commit; both steps fail loudly
let write_txn = collab_db.write_txn();
write_txn.flush_doc(self.uid, workspace_id.as_str(), object_id,
  encoded_collab.state_vector.to_vec(), encoded_collab.doc_state.to_vec())
  .map_err(|err| CollabError::Internal(err.into()))?;
write_txn.commit_transaction().map_err(|err| CollabError::Internal(err.into()))?;
```

**Flow:** Load: existence check → single mutable transaction → `load_doc_with_txn` applies every stored update into that txn (load errors are LOGGED not fatal — the doc opens with whatever applied) → read-txn dropped → txn committed. Save: encode outside (`encode_collab_v1` with type validation at call sites) → `flush_doc` writes sv+doc_state into the write txn → `commit_transaction()`. The same `(uid, workspace_id, object_id)` triple keys every call; `is_doc_exist` uses it too.
**Invariant:** The load transaction is committed even when individual update application errored (partial state beats no state for CRDTs); a `flush_doc` without `commit_transaction` persists NOTHING — the explicit commit is part of the contract. Read txn must be dropped before committing the write-side mutation txn (ordering visible at :461-463).
**Probe:** `/tmp/extcollab-af-probe` t01-t10 cover dispatch/task kernels; this seam's pins verified by byte-exact source reads at HEAD (`load_collab_from_disk`, `save_collab_to_disk`). Upstream suite blocked: `cargo test -p flowy-document` fails building `librocksdb-sys` C++ in this environment (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "CollabPersistenceImpl load_collab_from_disk load_doc_with_txn", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase flush (stage + explicit commit) and log-not-fail load semantics. Adapt storage engine freely — the contract is only "updates replay inside one transaction". Omit the wasm/IndexedDB twin unless porting to browser.
