<!-- capsule-v2 -->
# Nested async transactions — how do you make execTransaction nestable and strictly ordered on a single connection?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do nested transactions merge into one BEGIN/COMMIT unit while concurrent top-level calls still serialize in call order — without an actual DB savepoint?

## AsyncLocalStorage nesting + promise-chained serialization
**Path/Symbol:** `app/server/lib/SQLiteDB.ts:SQLiteDB.execTransaction` (438–464), `_execTransactionImpl` (517–535), `_prevTransaction` field (260), `asyncLocalStorage` module const (94), `_inTransaction` getter (616–618).
**Signature:** `async execTransaction<T>(callback: () => Promise<T>): Promise<T>`.
**Data Shape:** `_prevTransaction: Promise<any>` — the tail of a chain of serialized transaction promises; AsyncLocalStorage stores `boolean` (in-transaction marker) per async context.

### Decisive source
```ts
public async execTransaction<T>(callback: () => Promise<T>): Promise<T> {
  // If in a transaction, merge any nested transactions into the main one.
  if (this._inTransaction) { return callback(); }
  await this._applyPause();
  try {
    return await (
      this._prevTransaction =
        this._prevTransaction.catch(noop).then(     // wait for the PREVIOUS tx (swallow errors)
          () => asyncLocalStorage.run(true, () => this._execTransactionImpl(callback)),
        )
    );
  } finally {
    if (this._needVacuum) { await this.requestVacuum(); }   // deferred VACUUM after commit
  }
}
private async _execTransactionImpl<T>(callback: () => Promise<T>): Promise<T> {
  await this.exec("BEGIN");
  try {
    const value = await callback();       // nested calls see _inTransaction=true via ALS
    await this.exec("COMMIT");
    return value;
  } catch (err) {
    try { await this.exec("ROLLBACK"); }
    catch (rollbackErr) { log.error("Rollback failed: %s", rollbackErr); }
    throw err;                            // original error, not the rollback error
  }
}
```

**Flow:** call → ALS store set? ⇒ plain `await callback()` (joins the ambient transaction; no new BEGIN) → else queue behind `_prevTransaction` (previous failures swallowed so one rollback doesn't poison the chain) → run BEGIN → callback → COMMIT under `asyncLocalStorage.run(true, ...)` so every async descendant inherits the marker → error ⇒ ROLLBACK with double-failure guard, rethrow ORIGINAL error. Later calls started in quick succession wait for earlier ones because each reassigns `_prevTransaction` before awaiting.
**Invariant:** nesting is detected by async context, NOT by a counter — a callback that spawns un-awaited async work loses the marker and gets its own transaction later; exactly one physical BEGIN/COMMIT per top-level entry, so "nested rollback" is all-or-nothing by design (the test suite pins group-rollback explicitly); transactions are strictly ordered even when started concurrently — callers may rely on prior transactions having committed; nothing inside a transaction honors write-pauses (would deadlock against a pending COMMIT).
**Probe:** `test/server/lib/SQLiteDB.ts` `describe("execTransaction")` — `"should serialize execTransaction calls"` (:404), `"should allow nested execTransaction calls"` (:437), `"should rollback nested execTransaction calls as a group"` (:449), `"should nest execTransaction calls robustly regardless of timing"` (:464); pause interplay :492,:553.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "execTransaction asyncLocalStorage _prevTransaction", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any single-connection embedded DB (SQLite everywhere): ALS-based join semantics + previous-promise chaining gives nestable, ordered, all-or-nothing transactions in ~30 lines with zero engine features. Adapt the context carrier (ALS → zone/AsyncContext/contextvars equivalent) and the vacuum/pause hooks to host. Omit if your driver exposes real savepoints AND you need partial inner rollback — grist deliberately chose merged-unit semantics instead.
