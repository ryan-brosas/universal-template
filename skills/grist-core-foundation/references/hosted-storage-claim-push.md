<!-- capsule-v2 -->
# Hosted Storage Claim & Push — how do you make a local file the single source of truth for a worker, then push it to eventually-consistent object storage without losing or duplicating work?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** For a multi-worker hosted doc store, what ordering guarantees make `prepareLocalDoc`/`markAsChanged`/`flushDoc`/`_pushToS3` safe against parallel opens, dirty-but-clean files, and S3 eventual consistency?

## claim → local-first → checksum-verified push ladder
**Path/Symbol:** `app/server/lib/HostedStorageManager.ts` — `prepareLocalDoc` (:251–267), `_claimDocument` (:614–689), `markAsChanged` (:499–524), `flushDoc` (:484–494), `_pushToS3` (:768–823), `_fetchFromS3` (:716–733), `_wipeCache` (:694–702), `closeDocument` (:473–479), `closeStorage` (:415–429).
**Signature:** `prepareLocalDoc(docName, srcDocName?): Promise<boolean>` (true = new); `markAsChanged(docName, reason?): void`; `flushDoc(docName): Promise<void>`; `_pushToS3(docId): Promise<void>`.
**Data Shape:** `_localFiles: Map<docId, Promise<boolean>>` (single-flight claim), `_prepareFiles: Set<docId>` (parallel-open guard), `_uploads: KeyedOps` (debounced push queue), `_latestVersions/_latestMetaVersions: Map`, `_timestamps: Map`, `_labels: Map`, `_snapshotProgress: Map`.

### Decisive source
```ts
public async prepareLocalDoc(docName, srcDocName?) {
  await this.closeDocument(docName);              // wait out any in-flight close
  if (this._prepareFiles.has(docName)) {
    throw new Error(`Tried to call prepareLocalDoc('${docName}') twice in parallel`);
  }
  try {
    this._prepareFiles.add(docName);
    const isNew = !(await this._claimDocument(docName, srcDocName));
    return isNew;
  } finally { this._prepareFiles.delete(docName); }
}
// _claimDocument: mapGetOrSet single-flights the whole claim; then decides local-vs-S3:
const existsLocally = await fse.pathExists(this.getPath(docName));
if (existsLocally) {
  if (!docStatus.docMD5 || docStatus.docMD5 === DELETED_TOKEN || docStatus.docMD5 === "unknown") {
    const head = await this._ext.head(docName);
    if (head && lastLocalVersionSeen !== head.snapshotId) { await this._wipeCache(docName); }
    else { return true; }                            // local wins when S3 state unknown
  } else {
    const checksum = await this._getHash(await this._prepareBackup(docName));
    if (checksum === docStatus.docMD5) { return true; }   // checksum match => accept local
    else { await this._wipeCache(docName); }              // mismatch => S3 is canonical, wipe
  }
}
return this._fetchFromS3(docName, { sourceDocId: srcDocName, trunkId, snapshotId, canCreateFork });
```
Push side (`markAsChanged` → `_uploads.addOperation` → `_pushToS3`): skips if `_prepareFiles.has(docId)` ("too soon to consider pushing"), makes a backup, reads metadata, calls `_inventory.uploadAndAdd` which calls `_ext.upload`; if the checksummed store returns `Unchanged`, nothing new is pushed and `skippedPushes++`; otherwise `_onInventoryChange` schedules a prune.

**Flow:** every open first waits for a prior close of the same doc; a `_prepareFiles` guard rejects true parallel `prepareLocalDoc` calls; `_claimDocument` single-flights via `mapGetOrSet` and asserts the doc is active on THIS worker (redis `getDocWorkerOrAssign`); local file present + redis MD5 unknown/absent ⇒ prefer local unless S3 has a newer version; local present + redis MD5 known ⇒ checksum-compare, mismatch wipes local and defers to S3; absent ⇒ `_fetchFromS3` (fork/snapshot fallback to trunk, `NEW_DOCUMENT_CODE` trunk ⇒ empty). Writes flow through `markAsChanged` → debounced `KeyedOps` push; `flushDoc` loops `expediteOperationAndWait` + inventory flush until `isAllSaved` (with 1s throttle to avoid a hot loop).
**Invariant:** (1) Parallel `prepareLocalDoc` on the same doc is treated as a BUG and throws — the single-flight + guard combo means one claim wins, others fail loudly rather than racing. (2) Local file is trusted only when it matches the redis checksum or S3 state is unknown; any mismatch defers to S3 (canonical). (3) A push is never started while the doc is still being prepared (`_prepareFiles` check). (4) `markAsChanged` throws if called after `closeStorage` (`_closed`), surfacing use-after-close.
**Probe:** direct tests `test/server/lib/HostedStorageManager.ts`: "serializes parallel opening of same document" (:630, asserts `prepareLocalDoc` ×4 rejects `/in parallel/` while `fetchDoc` ×4 succeeds), "survives if there is a doc marked dirty that turns out to be clean" (:609), "viewing a document does not generally change it" (:755, `markAsChanged` call-count unchanged by reads), "can lose checksums without disruption with/without local file wipe" (:940), "doesn't wipe local docs when they exist on disk but not remote storage" (:1068), "does not overwrite remote doc on retriable error" (:1082).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "prepareLocalDoc _claimDocument markAsChanged flushDoc _pushToS3", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: close-before-open wait, parallel-open guard that throws, single-flight claim, checksum-verified local-trust decision, debounced push with in-prepare skip, and flush-until-saved loop. Adapt the store (S3 vs any object store), checksum storage (redis vs any shared KV), and timing. Omit Grist's fork/snapshot urlId algebra unless porting that model. The `markAsChanged`-after-close throw is a useful invariant to keep.
