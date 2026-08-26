<!-- capsule-v2 -->
# Snapshot inventory — how do you maintain a cheap version list for a store that gives you no listing metadata?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you avoid HEAD-per-version on every prune while staying correct when the object store's eventual consistency surprises you?

## Filesystem+object-store two-level cache with expect-checksum and full reconstruction
**Path/Symbol:** `app/server/lib/DocSnapshots.ts:DocSnapshotInventory` (94–313): `uploadAndAdd` (163–190), `_getSnapshots` (239–273), `_reconstruct` (291–307), `flush/_flush` (192–201, 309–314); serialization via per-doc `KeyedMutex`.
**Signature:** `versions(key, expectSnapshotId?): Promise<ObjSnapshotWithMetadata[]>`; `uploadAndAdd(key, upload: () => Promise<{snapshot?, prevSnapshotId}>)`.
**Data Shape:** inventory = newest-first JSON array of `{snapshotId, lastModified, metadata}`; stored as an S3 object alongside the documents (`_meta` ExternalStorage) AND cached as a local file (`_getFilename(key)`); `_needFlush: Set<string>` marks dirty entries; every mutation runs inside `_mutex.runExclusive(key, ...)`.

### Decisive source
```ts
private async _getSnapshots(key, expectSnapshotId) {
  let data = await this._loadFromFile(fname);                       // L1: local disk
  if (data && expectSnapshotId && data[0]?.snapshotId !== expectSnapshotId) { data = null; }
  if (!data && await this._meta.exists(key)) {                      // L2: object store copy
    await fse.remove(fname); await this._meta.download(key, fname);
    data = await this._loadFromFile(fname);
    if (data && expectSnapshotId && data[0]?.snapshotId !== expectSnapshotId) { data = null; }
  }
  if (!data) {                                                      // L3: HEAD every version
    data = await this._reconstruct(key);
    // Reconstructed data is precious. Make sure it gets saved.
    await this._saveToFile(fname, data); this._needFlush.add(key);
  }
  return data;
}
// uploadAndAdd serializes the actual upload WITH the inventory edit so the version
// list can never miss the snapshot the upload just created:
await this._mutex.runExclusive(key, async () => {
  const { snapshot, prevSnapshotId } = await upload();
  const snapshots = await this._getSnapshots(key, prevSnapshotId);   // cross-check head id
  if (snapshots[0]?.snapshotId === snapshot.snapshotId) { return; }  // already added (reconstruction race)
  snapshots.unshift(snapshot); ...this._needFlush.add(key);
});
```

**Flow:** read ⇒ local file → validate newest-id against caller's expectation → object-store copy → same validation → else reconstruct by HEADing each version's metadata (expensive, rare), persist result locally and mark dirty for later S3 flush. Write ⇒ `uploadAndAdd` runs the caller's real upload INSIDE the same per-key critical section as the list update, using `prevSnapshotId` as a consistency cross-check: mismatch ⇒ discard cache and reload from authoritative sources; duplicate add after reconstruction is detected by snapshotId and skipped.
**Invariant:** the inventory is a CACHE, never the source of truth — any level can be wrong and falls through to reconstruction; the upload callback must be atomic with the list edit or the store's version list and the inventory diverge ("surprise" reloads); flushes are deferred (`_needFlush`) so N edits cost one S3 write; all operations for one document serialize on a KeyedMutex, making reasoning single-threaded per key. The file's header records why the list lives in S3 rather than db/redis/dynamo (sharding, load, ops cost).
**Probe:** `test/server/lib/DocSnapshots.ts::DocSnapshotInventory` section — add/expect-mismatch/reconstruct flows against a fake ExternalStorage; pruner tests (:11–85) exercise `classify()` over the inventory.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "DocSnapshotInventory _reconstruct uploadAndAdd", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any append-only versioned blob store lacking rich listings (S3-class): two-level cached manifest + expect-head validation + serialized upload-and-record + rare full reconstruction. Adapt storage layers (local tmpdir + bucket), mutex choice (KeyedMutex capsule), and metadata normalization to host. Omit the snapshotWindow plumbing (see snapshot-retention capsule for policy).
