<!-- capsule-v2 -->
# Batched pre-upload with staleness cache — how do you cut round-trips without uploading stale bytes?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How does multiPut batching co-exist with the per-item upload loop, and when is the pre-upload result discarded?

## ItemUploader
**Path/Symbol:** `packages/lib/services/synchronizer/ItemUploader.ts` :15-112; consumer `packages/lib/Synchronizer.ts` :493 + :629 (preUploadItems) + :813 (serializeAndUploadItem).
**Signature:** `preUploadItems(items: BaseItemEntity[]): Promise<void>`; `serializeAndUploadItem(ItemClass, path, local): Promise<void>`; `maxBatchSize = 1MB`.
**Data Shape:** `preUploadedItems_: Record<path, { error?: { message?, code? } }>`; parallel `preUploadedItemUpdatedTimes_: Record<path, number>`.

### Decisive source
```ts
public async serializeAndUploadItem(ItemClass, path, local) {
    const preUploadItem = this.preUploadedItems_[path];
    if (preUploadItem) {
        if (this.preUploadedItemUpdatedTimes_[path] !== local.updated_time) {
            // ...item has been changed between pre-upload and processing → re-upload regular way
            logger.warn(`Pre-uploaded item updated_time has changed. It is going to be re-uploaded again: ${path} (...)`);
        } else {
            const error = preUploadItem.error;
            if (error) throw new JoplinError(error.message ? error.message : 'Unknown pre-upload error', error.code);
            return;                                  // cache hit: bytes already on target
        }
    }
    const content = await ItemClass.serializeForSync(local);
    await this.apiCall_('put', path, content);
}
```
Batching rules: only when `api_.supportsMultiPut`; resources EXCLUDED (blob must precede metadata); oversize items skipped from batching (`itemSize > maxBatchSize` → regular path later); greedy size-bounded batches; batch errors are returned PER ITEM inside `response.items` and replayed as JoplinErrors at consume time.

**Flow:** start() filters never-synced items into preUploadItems → serialized bodies fly in bulk → the main loop's serializeAndUploadItem hits the cache (zero extra calls) unless updated_time moved — then it transparently re-uploads. Direct tests pin all four behaviors: batching+cache hit (:58), oversize exclusion (:89), stale-cache re-upload (:103), max-size respect (:124), per-item error rethrow (:145) — all in `packages/lib/services/synchronizer/ItemUploader.test.ts`.
**Invariants:** (1) cache validity = exact updated_time equality, not path presence; (2) a FAILED pre-upload must surface at consume time with its original code (`rejectedByTarget` classification still works downstream); (3) resources never ride the batch because metadata-without-blob breaks ordering guarantees; (4) the 1MB bound is per BATCH (name.length + body.length accounting), oversized singletons degrade to plain puts.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "this.preUploadedItemUpdatedTimes_[path] !== local.updated_time" packages/lib/services/synchronizer/ItemUploader.ts && grep -cF "itemSize > this.maxBatchSize) continue;" packages/lib/services/synchronizer/ItemUploader.ts && grep -c "ModelType.Resource) continue;" packages/lib/services/synchronizer/ItemUploader.ts'` (anchored at repo root; expects 1 / 1 / 1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "ItemUploader preUploadItems serializeAndUploadItem multiPut supportsMultiPut", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: write-through pre-upload cache keyed by content version, per-item error replay, resource/oversize exclusions. Adapt: batch transport to your API. Omit: nothing — this module ports nearly verbatim.
