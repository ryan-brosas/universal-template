<!-- capsule-v2 -->
# Client-side merge execution plane — what must the TypeScript wrapper sanitize before and after the WASM boundary?

**Source:** aliasvault AGPL-3.0 (patterns-only) `main@95903e926f757046ef32feb7ca147900de0a6802`; Codebase Memory `ext-aliasvault`. **Question:** Which JS↔Rust value conversions can silently corrupt a merge, and where are they guarded?

## Sanitize-execute-export loop
**Path/Symbol:** `apps/browser-extension/src/utils/VaultMergeService.ts:169-243` (`merge`), :277-298 (`prune`), :349-359 (`exportDatabase`), :377-393 (`readQueryAsJson`).
**Signature:** `async merge(localVaultBase64: string, serverVaultBase64: string): Promise<MergeResult>`; `async prune(vaultBase64: string, retentionDays = TRASH_RETENTION_DAYS): Promise<PruneResult>`.
**Data Shape:** Both vaults travel as base64 SQLite strings; sql.js loads them in memory; Rust receives `{ local_tables, server_tables }` JSON and returns `{ success, statements, stats }` (snake_case keys mapped to camelCase by hand at :226-232).

### Decisive source
```ts
// Execute SQL statements from Rust on local database
for (const stmt of mergeOutput.statements) {
  // Convert undefined to null for sql.js (serde-wasm-bindgen may convert null to undefined)
  const sanitizedParams = stmt.params.map(p => p === undefined ? null : p);
  localDb.run(stmt.sql, sanitizedParams);
}
// Export the merged database
const mergedVaultBase64 = this.exportDatabase(localDb);
```
```ts
private exportDatabase(db: Database): string {
  db.run('VACUUM');
  const binaryArray = db.export();
  // Convert to string in chunks to avoid O(n²) byte-by-byte concatenation
  const chunkSize = 0x8000;
  ...
}
```

**Flow:** init WASM via `browser.runtime.getURL('src/aliasvault_core_bg.wasm')` → read all syncable tables (`getSyncableTableNames()` from Rust — never a JS list) → `JSON.parse(JSON.stringify(x))` THREE times (:199 input, :283 prune input, :387 per-record) to kill `undefined` before serde → run statements with undefined→null param fix → `VACUUM` then chunked base64 export → both DBs closed in `finally`.
**Invariants:** (1) The table-name list comes FROM Rust so JS and Rust schemas can't diverge. (2) serde-wasm-bindgen maps JSON null to JS undefined on the way OUT — every param list must re-map or sql.js binds wrong. (3) Prune short-circuit: zero statements ⇒ return the ORIGINAL base64, skipping VACUUM/export entirely (:293-299). (4) Chunked String.fromCharCode (0x8000) is required — naive per-byte loops hit stack limits on vault-sized exports.
**Probe:** `grep -c 'p === undefined ? null : p' apps/browser-extension/src/utils/VaultMergeService.ts` → `2`; `grep -c 'JSON.parse(JSON.stringify(' apps/browser-extension/src/utils/VaultMergeService.ts` → `3`; `grep -c '0x8000' apps/browser-extension/src/utils/VaultMergeService.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aliasvault", query: "VaultMergeService", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sanitize→execute→vacuum→chunked-export envelope around a pure merge core; adapt storage engine; omit WXT/browser-extension specifics. Source confirmed at pin `95903e92`; jest runner unavailable in inspo clone (deterministic probes substituted).
