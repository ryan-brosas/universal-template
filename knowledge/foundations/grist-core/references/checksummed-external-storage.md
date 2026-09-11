<!-- capsule-v2 -->
# Checksummed External Storage — how do you make an eventually-consistent object store behave like a strongly-consistent one for uploads, downloads, existence checks, and deletes?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What retry/verification contract turns a raw S3-style store into one where a reader can trust what it fetched and a writer can skip redundant pushes — despite eventual consistency?

## Decorator with shared+local hash stores, retry-until-consistent, and Unchanged sentinel
**Path/Symbol:** `app/server/lib/ExternalStorage.ts` — `ChecksummedExternalStorage` (:176–408): `upload` (:199–222), `downloadTo` (:260–310), `remove` (:224–248), `versions` (:312–323), `_retry` (:350–378), `_retryWithExistenceCheck` (:384–398), `_keyWithSnapshot` (:405–407); `Unchanged = Symbol("Unchanged")` (:418); `DELETED_TOKEN = "*DELETED*"` (:13).
**Signature:** `upload(key, fname, metadata?): Promise<string | null | typeof Unchanged>`; `downloadTo(fromKey, toKey, fname, snapshotId?): Promise<string>`; `remove(key, snapshotIds?): Promise<void>`.
**Data Shape:** `_options` = `{maxRetries, initialDelayMs, localHash, sharedHash, latestVersion, computeFileHash}` — three PropStorages: local hash (file `{id}.grist-hash-{doc|meta}`), shared hash (redis), latestVersion (in-memory map).

### Decisive source
```ts
public async upload(key, fname, metadata?) {
  const checksum = await this._options.computeFileHash(fname);
  const prevChecksum = await this._options.localHash.load(key);
  if (prevChecksum && prevChecksum === checksum && !metadata?.label) {
    const snapshotId = await this._options.latestVersion.load(key);
    return Unchanged;                       // identical content, no push
  }
  const snapshotId = await this._ext.upload(key, fname, metadata);
  if (typeof snapshotId === "string") { await this._options.latestVersion.save(key, snapshotId); }
  await this._options.localHash.save(key, checksum);
  await this._options.sharedHash.save(key, checksum);
  return snapshotId;
}
// download: verify mutable data against shared hash
if (!snapshotId) {
  const expectedChecksum = await this._options.sharedHash.load(fromKey);
  if (expectedChecksum && expectedChecksum !== checksum) { log.warn("wrong checksum ..."); }
}
// _retry: retry while operation returns undefined OR throws a non-fatal error
while (backoffCount <= this._options.maxRetries) {
  try {
    const result = await operation();
    if (result !== undefined) { return result; }
    problems.push([Date.now() - start, "not ready"]);
  } catch (err) {
    if (this._ext.isFatalError(err)) { throw err; }
    problems.push([Date.now() - start, err]);
  }
  await delay(Math.round(backoffFactor));   // backoffFactor *= 1.7 each round
  if (this._closed) { throw new Error("storage closed"); }
  backoffCount++;
}
throw new Error(`operation failed to become consistent: ${name} - ${problems}`);
```

**Flow:** upload computes the file hash and short-circuits to `Unchanged` when local hash matches and no label is present (label forces a re-push so labeled backups are distinct); otherwise uploads and records the new snapshot id + local + shared hashes. download streams to a temp file, computes its hash, and for mutable (non-snapshot) data warns on mismatch with the shared hash; renames into place with `overwrite:false`; saves latestVersion + localHash only when `fromKey === toKey` (fork downloads deliberately don't clobber the source's bookkeeping). remove forbids removing the most-recent version by id, and on full delete stamps `DELETED_TOKEN` into latestVersion + sharedHash (per-snapshot deletes stamp the snapshot-scoped key). `versions` returns `[]` when latest is `DELETED_TOKEN` and `undefined` (→retry) when the store's first version doesn't yet match the recorded latest. `_retry` retries `undefined` results and non-fatal errors with 1.7× backoff up to `maxRetries`; `_retryWithExistenceCheck` retries existence/head until the store agrees with the shared-hash expectation (expected-but-missing or unexpected-but-present both retry).
**Invariant:** (1) The `Unchanged` sentinel is the ONLY way a caller learns "nothing changed" — it must be handled distinctly from a real snapshot id (HostedStorageManager treats it as a skipped push, `skippedPushes++`). (2) Mutable reads are verified against the shared hash; snapshot reads skip the check because snapshots are immutable. (3) `DELETED_TOKEN` is a real string used as a tombstone in hash/version stores so a cleared/absent value is distinguishable from "deleted". (4) Fatal errors (per `isFatalError`) are rethrown immediately, never retried.
**Probe:** direct tests `test/server/lib/HostedStorageManager.ts` (the checksummed wrapper is exercised end-to-end): "can lose checksums without disruption with/without local file wipe" (:940), "does not overwrite remote doc on retriable error" (:1082), "should fail immediately (without retries) on fatal error" (:1128), "fetches remote docs if they don't exist locally" (:1150).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "ChecksummedExternalStorage _retry Unchanged DELETED_TOKEN upload", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the decorator shape: hash-based skip-push, hash-verified download, existence-check retry driven by a shared expectation store, tombstone sentinel, and fatal-error passthrough. Adapt the backoff factor/limits and where hashes live. Omit Grist's `_keyWithSnapshot` key algebra unless you version objects the same way. The `Unchanged` sentinel + `DELETED_TOKEN` tombstone are the two details a porter most often gets wrong.
