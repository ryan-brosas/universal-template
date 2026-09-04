<!-- capsule-v2 -->
# Server snapshot squash — updates-queue with read-time merge, timestamp-guarded upsert, and native/yjs codec ladder

**Source:** AFFiNE EE-licensed `packages/backend/server` (carve-out noted; pattern MIT-portable) `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** How does the server store Yjs docs so hot writes are cheap but reads always return a merged, validated binary — and what breaks under concurrent writers?

## DocStorageAdapter.getDoc / squash / models.doc.upsert
**Path/Symbol:** `packages/backend/server/src/core/doc/storage/doc.ts`: `getDoc` (:129-149), `squashUpdatesToSnapshot` (:172-207), `squash` (:299-322), `invalidDocUpdateReason` (:108-127); `packages/backend/server/src/models/doc.ts`: `upsert` (:177-202); `packages/backend/native/src/lib.rs`: `merge_updates_in_apply_way` (:36-45), `validate_doc_update` (:50-55).
**Signature:** `getDoc(spaceId, docId)` acquires per-doc lock (`SingletonLocker`, `await using`) then merges; raw SQL upsert with `ON CONFLICT ... WHERE updated_at <= $ts`.
**Data Shape:** DB rows: `snapshots(workspace_id, guid, blob, size, updated_at, updated_by)` + append-only `updates(id=docId, blob, createdAt)`; in-memory `DocRecord {spaceId, docId, bin, timestamp, editor}`.

### Decisive source
```ts
// READ PATH merges pending updates INTO the snapshot (write-back on read)
if (updates.length) {
  const docUpdate = await this.squash(snapshot ? [snapshot, ...updates] : updates);
  return await this.squashUpdatesToSnapshot(spaceId, docId, updates, snapshot, docUpdate);
}
```
```sql
-- models.doc.upsert: concurrent-writer guard lives IN the WHERE clause
INSERT INTO "snapshots" (...) VALUES (...)
ON CONFLICT ("workspace_id", "guid")
DO UPDATE SET "blob" = ${blob}, ..., "updated_at" = ${updatedAt}, "updated_by" = ${editorId}
WHERE "snapshots"."workspace_id" = ${spaceId} AND "snapshots"."guid" = ${docId}
  AND "snapshots"."updated_at" <= ${updatedAt}
RETURNING ...
-- zero rows returned = another process already wrote a newer snapshot; that's FINE
```
```rust
// native codec: y-octo decodes WITHOUT building full doc state for validation
pub fn merge_updates_in_apply_way(updates: Vec<Buffer>) -> Result<Buffer> {
  let mut doc = Doc::default();
  for update in updates { doc.apply_update_from_binary_v1(update.as_ref())?; }
  Ok(doc.encode_update_v1()?.into())
}
pub async fn validate_doc_update(update: Buffer) -> Result<bool> {
  tokio::task::spawn_blocking(move || Update::decode_v1(update).is_ok()).await...
}
```

**Flow:** push path validates each incoming update (`decode_v1` off-thread, 1 s timeout, 32 MiB cap; oversized ⇒ dropped 'oversized', decode-crash ⇒ accepted-by-default) and appends to `updates`. Read path locks the doc → squash `[snapshot, ...pending]` → transactional write-back: set new snapshot, archive OLD snapshot into `snapshotHistory`, mark updates merged. Merge engine ladder: yjs JS merge by default, native y-octo apply-way for big jobs (`nativeApplyUpdates` at getDocBinNative :162), broadcast compression uses native with fallback to batch on error.

**Invariant:** (1) The `updated_at <=` guard makes snapshot writes idempotent under multi-process races — LOSING the race is correct because CRDT updates are commutative; porters who "fix" it to `<` re-introduce lost-update windows where an equal-timestamp write is dropped. (2) Squash keeps `timestamp = LAST update's timestamp` (not now()) so the guard compares user-time, not server-time. (3) Validation fails OPEN (catch → null → accept): a broken validator must not become a write outage. (4) History rows are created from the PRE-squash snapshot only when write-back succeeded — ordering matters or history records future state.

**Probe:** `packages/backend/server/src/__tests__/doc/workspace.spec.ts` :134-188 pins read-path merge ('helloworld' after second update + getDoc); :228-279 pins the timestamp guard end-to-end (faked-newer snapshot blocks record update BUT content still merges and pending updates are consumed, `db.update.count() === 0`). Native decode boundary pinned by rust tests lib.rs :82-84 (`[0,0] ok`, `[0] err`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "DocStorageAdapter squash squashUpdatesToSnapshot setDocSnapshot validateDocUpdate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt read-time squash + guarded upsert + fail-open validation; adapt storage engine and lock primitives; omit the EE-licensed code itself when licensing requires — the CONTRACT is what ports.
