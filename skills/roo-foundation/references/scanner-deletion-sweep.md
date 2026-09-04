<!-- capsule-v2 -->
# End-of-scan deletion sweep — what counts as "removed" when the cache outlives the file list?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** Which cached paths get their points deleted at scan end, and can that sweep misfire?

## Absence-from-processed-set is the deletion predicate
**Path/Symbol:** `src/services/code-index/processors/scanner.ts:scanDirectory` (:326-360).
**Signature:** `const oldHashes = this.cacheManager.getAllHashes(); for (const cachedFilePath of Object.keys(oldHashes)) { if (!processedFiles.has(cachedFilePath)) {...} }`.
**Data Shape:** `processedFiles: Set<string>` — populated ONLY after a successful `stat` + `readFile` + hash (:147); `getAllHashes()` returns a shallow copy.

### Decisive source
```ts
if (!processedFiles.has(cachedFilePath)) {
  await this.qdrantClient.deletePointsByFilePath(cachedFilePath)
  await this.cacheManager.deleteHash(cachedFilePath)
}
```

**Flow:** after all batches drain (and an abort check), every cache key not seen during THIS scan is treated as deleted-or-no-longer-indexable: its Qdrant points are purged and its cache entry removed. Deletion errors here are logged + `onError`-reported but do NOT abort the scan.
**Invariant / trap:** "unreadable" ≡ "deleted" in this design. A transient IO error (EBUSY, permission blip) makes the file miss `processedFiles`, so its vectors are purged; recovery comes only from the NEXT scan re-indexing it. Porters must keep this coupling or add their own retry-before-purge step.
**Probe:** `src/services/code-index/processors/__tests__/scanner.spec.ts` ("should delete points for removed files" :212-218 pins exactly the absent-path deletion call pair); executed pin :328/:332.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "DirectoryScanner getAllHashes processedFiles deletePointsByFilePath", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt the sweep as the only stale-vector GC (incremental scans never revisit vanished files otherwise). Adapt: consider stat-retry or grace-window before purging if your host has flaky IO. Omit vscode fs usage. Coverage caveat: no spec exercises the unreadable-file purge case — behavior confirmed by source read only.
