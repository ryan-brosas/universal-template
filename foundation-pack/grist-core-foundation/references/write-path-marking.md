<!-- capsule-v2 -->
# Write-path change marking — how does every mutation reliably flag "this document is dirty" without each caller remembering to do it?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you guarantee that no write escapes persistence bookkeeping (dirty-flag + cache invalidation), even when writes go through many different methods?

## Promise-decorated write API: markAsChanged in `finally`
**Path/Symbol:** `app/server/lib/DocStorage.ts:_markAsChanged` (:1701–1708) wrapping `run` (:1539), `exec` (:1543), `execTransaction` (:1555), `runAndGetId` (:1560), `requestVacuum` (:1565); explicit call in `removeUnusedAttachments` (:1522–1524).
**Signature:** `private async _markAsChanged<T>(promise: Promise<T>): Promise<T>`.
**Data Shape:** Marks = `this._cachedDataSize = null` + `storageManager.markAsChanged(docName)` (fire-and-forget upstream signal).

### Decisive source
```ts
private async _markAsChanged<T>(promise: Promise<T>): Promise<T> {
  try {
    return await promise;
  } finally {
    this._cachedDataSize = null;               // size cache now stale
    this.storageManager.markAsChanged(this.docName);   // schedule doc save/upload
  }
}
```

**Flow:** every mutating entrypoint (`run`, `exec`, `execTransaction`, `runAndGetId`, `requestVacuum`) wraps its promise in `_markAsChanged` → success OR failure, the doc is flagged changed and the byte-size cache dropped → non-mutating readers (`all`, `get`, `prepare`) deliberately do NOT wrap → rare direct `db.run(...)` calls (attachment GC) must call the manager explicitly after checking `result.changes > 0`.
**Invariant:** Marking happens even when the write FAILS — after a failed write the on-disk state may differ from memory, so treating the doc as clean would risk losing data; conversely pure reads never mark (no upload churn). The size cache shares the invalidation so quota checks can't serve pre-write numbers. Porters who mark only on success introduce silent data loss on partial failure.
**Probe:** No dedicated test file pins this decorator directly; behavior is exercised indirectly by every DocStorage.js test through `applyStoredActions` (writes land via wrapped `run`/`exec`). Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "_markAsChanged markAsChanged storageManager", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the decorate-every-write-path pattern for any store with deferred persistence (dirty-flag → periodic snapshotter): put marking in the lowest shared wrapper, in a `finally`, covering failures. Adapt what "changed" triggers (fs mtime bump, object-store upload enqueue, replication tick). Omit nothing — but keep the reader/writer asymmetry deliberate and documented.
