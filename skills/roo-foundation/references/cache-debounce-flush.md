<!-- capsule-v2 -->
# CacheManager debounce — why must shutdown flush an in-memory hash map explicitly?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** What are the write semantics of the scan-side cache, and where can its latest state be lost?

## 1500ms debounced JSON writes; flush() is the durability handle
**Path/Symbol:** `src/services/code-index/cache-manager.ts` (:10-110).
**Signature:** `getHash/getAllHashes/updateHash/deleteHash/clearCacheFile/flush(): Promise<void>`; cache file = `globalStorageUri/roo-index-cache-${sha256(workspacePath)}.json`.
**Data Shape:** `fileHashes: Record<string, string>` — the ONLY persisted index state; keyed by absolute fsPath.

### Decisive source
```ts
this._debouncedSaveCache = debounce(async () => { await this._performSave() }, 1500)
async flush(): Promise<void> { await this._performSave() }
```

**Flow:** every update/delete re-arms a 1.5s timer; the orchestrator calls `flush()` on EVERY early-return path (abort mid-scan :181/:242/:300) precisely because pending hashes otherwise die with the process; `clearCacheFile()` writes `{}` AND resets memory (it does NOT go through the debounce); load failures silently start empty (`catch → {}`), which makes a corrupt cache indistinguishable from "never indexed" ⇒ one full re-embed, not data loss.
**Invariant:** memory is authoritative during a run; disk is a checkpoint. Any port with worker processes or crash-safety needs must call flush at the same lifecycle points or accept re-indexing windows. Filename hashing means two workspace paths never share a cache file — but case-only path differences on macOS WILL create twin caches.
**Probe:** `src/services/code-index/__tests__/cache-manager.spec.ts`; executed pins: filename pattern + debounce constant.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "CacheManager _debouncedSaveCache flush clearCacheFile", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt map+debounce+explicit-flush-on-stop shape and per-workspace hashed filenames. Adapt storage location and serialization (safeWriteJson is atomic-ish via temp+rename). Omit vscode Uri plumbing.
