<!-- capsule-v2 -->
# File-watcher upsert no-op — do watcher-detected changes ever reach the vector store at this pin?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** After the watcher prepares points for changed files, what actually writes them to Qdrant?

## Phase-3 stub discards its inputs
**Path/Symbol:** `src/services/code-index/processors/file-watcher.ts:_executeBatchUpsertOperations` (:311-318).
**Signature:** `private async _executeBatchUpsertOperations(pointsForBatchUpsert: PointStruct[], successfullyProcessedForUpsert: Array<{path: string; newHash?: string}>, batchResults: FileProcessingResult[], overallBatchError?: Error): Promise<Error | undefined>`.
**Data Shape:** receives fully-prepared `PointStruct[]` (from `_processFilesAndPrepareUpserts`, which DID embed blocks) plus the hash-update ledger — and returns its fourth argument untouched.

### Decisive source
```ts
private async _executeBatchUpsertOperations(
  pointsForBatchUpsert: PointStruct[],
  successfullyProcessedForUpsert: Array<{ path: string; newHash?: string }>,
  batchResults: FileProcessingResult[],
  overallBatchError?: Error,
): Promise<Error | undefined> {
  return overallBatchError
}
```

**Flow:** event map (500ms debounce, later events OVERWRITE earlier ones per path) → categorize delete vs create/change → deletions recorded → files read/parsed/embedded in chunks of 10 (`Promise.allSettled`) → points land in `pointsForBatchUpsert`… and stop there. `upsertPoints` is never called; `successfullyProcessedForUpsert` (with fresh hashes) is never applied to the CacheManager.
**Invariant / consequence:** on this branch of the codebase, live edits reach the index only via the NEXT full/incremental scan (hash unchanged in cache ⇒ file re-read). A porter must NOT "adopt" the no-op as intentional behavior: wire phase 3 to `vectorStore.upsertPoints(points)` + `cacheManager.updateHash(path,newHash)` per entry, or your watcher will silently no-op too. The dead parameters are the tell.
**Probe:** deterministic pins executed byte-exact: fn body :311-318 returns arg; `grep -c 'upsertPoints' file-watcher.ts = 0`; `grep -c segmentHash = 0`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "FileWatcher processBatch _executeBatchUpsertOperations _processFilesAndPrepareUpserts", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Omit-as-is (it is a defect/stub); adopt the surrounding three-phase pipeline shape. Adapt by implementing phase 3 for real. Coverage caveat: NO spec covers `_executeBatchUpsertOperations`; file-watcher.spec exercises filtering/dispose only — the whole upsert path is source-read verified exclusively.
