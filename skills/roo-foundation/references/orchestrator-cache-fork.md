<!-- capsule-v2 -->
# Cache-vs-Qdrant preservation fork — which local state survives an indexing failure?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** After a failed `startIndexing`, when is the file-hash cache cleared versus preserved?

## The fork is "did we ever reach the store", not "how far did we get"
**Path/Symbol:** `src/services/code-index/orchestrator.ts:startIndexing` (`indexingStarted` flag :124; catch handler :296-336).
**Signature:** `let indexingStarted = false` → set true immediately AFTER `vectorStore.initialize()` resolves (:127-130).
**Data Shape:** catch path: abort-like errors (name AbortError or signal.aborted) ⇒ Standby + cache flush + watcher stop, NOT an error; real errors with `indexingStarted=true` ⇒ `clearCollection()` + `clearCacheFile()`.

### Decisive source
```ts
if (indexingStarted) {
  // Indexing started but failed mid-way - clear cache to avoid cache-Qdrant mismatch
  await this.cacheManager.clearCacheFile()
} else {
  // Never connected to Qdrant - preserve cache for future incremental scan
}
```

**Flow:** connection succeeded then scan died mid-way ⇒ collection wiped AND cache wiped together (both sides reset in lockstep); connection itself failed ⇒ collection untouched, cache PRESERVED so the next successful start can incremental-scan instead of re-embedding everything. `stopWatcher()` deliberately skips its Standby transition when state is Error/Stopping.
**Invariant:** never clear exactly one side — a cache that says "indexed" over a wiped collection permanently hides files; a wiped cache over live vectors merely costs one full rescan. Asymmetric failure handling must preserve this pairing.
**Probe:** deterministic pins executed: `if (indexingStarted)` ×2 sites; abort-first ordering (:180/:241/:298); `clearCacheFile` also on fresh-collection creation (:132-134).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "startIndexing indexingStarted clearCacheFile clearCollection", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt the two-state fork keyed on store-connectivity. Adapt cleanup to your store's delete semantics. Omit vscode workspace guards. Caveat: orchestrator.spec mocks the vector store; the fork's both-sides behavior is pinned by source read + these executed line-pins.
