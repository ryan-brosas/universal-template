<!-- capsule-v2 -->
# Scanner cache consistency — when may a file's hash enter the local cache?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** When is a changed file's new hash persisted to the disk cache relative to the Qdrant write?

## Hash-writes trail successful upserts
**Path/Symbol:** `src/services/code-index/processors/scanner.ts:scanDirectory/processBatch` (:150-156 unchanged-skip; :244 non-batch write; :443-446 post-success write).
**Signature:** `processBatch(batchBlocks, batchTexts, batchFileInfos, scanWorkspace, onError?, onBlocksIndexed?)`.
**Data Shape:** `batchFileInfos = { filePath, fileHash, isNew }[]` accumulated per file; `CacheManager` is a `{path → sha256}` record debounced 1500ms to `roo-index-cache-<sha256(workspace)>.json`.

### Decisive source
```ts
// inside processBatch, AFTER upsertPoints(...) succeeds:
for (const fileInfo of batchFileInfos) {
  await this.cacheManager.updateHash(fileInfo.filePath, fileInfo.fileHash)
}
success = true
```

**Flow:** read file → hash → `getHash` equal ⇒ skip; else parse blocks into mutex-guarded batch accumulators → dispatch at threshold 60 (`MAX_PENDING_BATCHES=20` backpressure loop awaits any in-flight batch) → per batch: delete-old-points (modified files only, NOT new ones) → embed → upsert → ONLY NOW update hashes. Batch retries use `500ms × 2^(n−1)` backoff, 3 attempts; after final failure the hashes are never written, so the next scan re-indexes those files.
**Invariant:** the cache must never claim a file is indexed when its points are not in Qdrant — cache and store are kept consistent BY WRITE ORDERING, not transactions. A port that updates hashes eagerly creates permanently invisible files.
**Probe:** `src/services/code-index/processors/__tests__/scanner.spec.ts` ("should process embeddings for new/changed files" :192, "should delete points for removed files" :212); executed pins :445 + threshold/backpressure greps.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "DirectoryScanner scanDirectory updateHash processBatch", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt write-ordering (hash strictly after successful upsert), delete-before-upsert for modified-but-not-new files only, and the pending-batch ceiling as a memory guard. Adapt constants (60/20/10-concurrency). Omit vscode config plumbing for `embeddingBatchSize`. Caveat: a failed deletion (:396-413) throws and aborts the whole batch BEFORE embedding — deletion failure blocks reindex of that batch by design (fail loud).
