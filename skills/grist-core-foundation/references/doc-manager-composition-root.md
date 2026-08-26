<!-- capsule-v2 -->
# DocManager composition root — how are active documents cached, opened, muted-waited, and their SQLite handles registered?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How does DocManager keep one ActiveDoc per docName, wait out a muted (shutting-down) doc, and expose the live SQLite handle without deadlocking?

## Promise-cached ActiveDoc map + unmuted-wait + SQLite registry
**Path/Symbol:** `app/server/lib/DocManager.ts` — `_activeDocs` (:81-84), `fetchDoc` (:588-595), `_withUnmutedDoc` (:622-636), `_fetchPossiblyMutedDoc` (:639-666), `_createActiveDoc` (:693-705), `registerSQLiteDB`/`unregisterSQLiteDB`/`getSQLiteDB` (:497-517), `markAsChanged` (:545-550), `renameDoc` (:519-532), `restoreTimingOn` (:113-115), `setRecovery` (:106-108).
**Signature:** `fetchDoc(docSession, docName, wantRecoveryMode?): Promise<ActiveDoc>`; `getSQLiteDB(docName): SQLiteDB | undefined`; `markAsChanged(activeDoc, reason?: "edit")`.
**Data Shape:** `_activeDocs = Map<docName, Promise<ActiveDoc>>` — the VALUE is a promise, so concurrent opens share one in-flight load. `_sqliteDbs = Map<docName, SQLiteDB>`. `_inRecovery`/`_inTimingOn` are `MapWithTTL` (30s / 10min).

### Decisive source
```ts
// _withUnmutedDoc — retry until the returned ActiveDoc is not shutting down
for (;;) {
  const { result, activeDoc } = await op();
  if (!activeDoc.muted) { return result; }
  log.debug("DocManager._withUnmutedDoc waiting because doc is muted", docName);
  await delay(1000);
}
```
```ts
// _fetchPossiblyMutedDoc — single-flight via mapSetOrClear on the promise map
if (!this._activeDocs.has(docName)) {
  activeDoc = await mapSetOrClear(this._activeDocs, docName,
    this._createActiveDoc(docSession, docName, wantRecoveryMode ?? this._inRecovery.get(docName))
      .then((newDoc) => { newDoc.on("backupMade", (bakPath) => this.emit("backupMade", bakPath)); return newDoc.loadDoc(docSession); }));
} else { activeDoc = await this._activeDocs.get(docName)!; }
```

**Flow:** `fetchDoc` wraps `_fetchPossiblyMutedDoc` in `_withUnmutedDoc`: if the doc is muted (shutting down), it polls every 1s until a fresh unmuted ActiveDoc is available. `_fetchPossiblyMutedDoc` re-opens in the desired recovery mode by shutting down a mismatched doc (owner-only), else single-flights creation through `mapSetOrClear` on the promise map (concurrent opens share one load). `_createActiveDoc` builds the ActiveDoc and restores its timing mode from `_inTimingOn`. `markAsChanged` forwards to the storage manager unless muted or mid-migration. `getSQLiteDB` returns the live handle from the registry — the comment warns it "could be closed at any time" (ActiveDoc registers it during init and unregisters on shutdown).
**Invariant:** the promise-valued map is the single-flight mechanism — a porter who stores the resolved ActiveDoc instead of the promise loses the dedupe and can double-load. The mute-wait loop is what lets a shutdown complete safely while new opens queue. `getSQLiteDB` must never be used to hold a handle across an await that could trigger shutdown (that's why ActiveDoc registers it only during initialization).
**Probe:** `test/server/lib/DocManager.ts` (or the HostedStorageManager suite) exercises open/fetch/mute behavior; the "serializes parallel opening of same document" test pins the single-flight.
**Coverage caveat:** the muted-wait loop timing is not unit-tested directly (exercised via shutdown/parallel-open suites); source-verified.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "DocManager fetchDoc _withUnmutedDoc _fetchPossiblyMutedDoc getSQLiteDB markAsChanged", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the promise-valued ActiveDoc map (single-flight), the muted-wait retry loop, and the SQLite-handle registry for any document server that must serialize opens against shutdowns; adapt the TTLs and recovery-mode semantics; omit the fork-mode owner bluff if you have no fork previews.
