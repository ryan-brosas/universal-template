<!-- capsule-v2 -->
# Undo-block compensating transaction — how do you give API handlers all-or-nothing semantics over an engine that applies actions live?

**Source:** grist-core (Apache-2.0), `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the correct transaction shape when the underlying store commits every applied action immediately and cannot roll back?

## startUndoBlock / runInUndoBlock
**Path/Symbol:** `app/server/lib/ActiveDocUtils.ts:startUndoBlock` (91-129), `runInUndoBlock` (136-150), `UndoBlock` interface (85-89).
**Signature:** `startUndoBlock(doc: ActiveDoc, docSession: OptDocSession): UndoBlock` where `UndoBlock = { applyUserActions(actions, options?): Promise<ApplyUAResult>; rollback(): Promise<void>; commit(): void }`; `runInUndoBlock<T>(doc, docSession, callback: (tx: UndoBlock) => Promise<T>): Promise<T>`.
**Data Shape:** Closure state: `applied: ApplyUAResult[]` (receipts of everything applied), `bundling: boolean` latch. Relies on the doc engine's bundle mode (`startBundleUserActions`/`stopBundleUserActions`) grouping all intermediate actions into ONE undo unit, and on `ApplyUAResult` carrying `{actionNum, actionHash}` per apply.

### Decisive source
```ts
let bundling = true;
// stopBundleUserActions always clears linkId, so guard against calling it twice
const stopBundling = () => {
  if (bundling) { bundling = false; doc.stopBundleUserActions(docSession); }
};
async rollback() {
  try {
    // Actions without a hash (e.g. no-op meta updates) can't be undone; skip them.
    const undoable = applied.filter(a => a.actionHash);
    if (undoable.length > 0) {
      await doc.applyUserActionsById(docSession,
        undoable.map(a => a.actionNum),
        undoable.map(a => a.actionHash!), true);
    }
  } finally { stopBundling(); }
}
commit() { stopBundling(); }

// runInUndoBlock: success commits, failure rolls back AND rethrows
try { const result = await callback(tx); tx.commit(); return result; }
catch (err) { await tx.rollback(); throw err; }
```

**Flow:** Begin → bundle ON. Handler applies actions through `tx.applyUserActions` (each result receipt collected). Success → `commit()` (bundle OFF, work stays). Failure → `rollback()` replays the collected receipts as compensating undos (`applyUserActionsById(..., true)`) then closes the bundle; error propagates. Unlike a DB transaction, applied actions are **visible immediately** — rollback issues compensating undo actions rather than discarding uncommitted work (comment at 74-79 says exactly this).
**Invariant:** Exactly-once bundle termination on EVERY path (double `stopBundleUserActions` would clear link state twice — hence the latch). Rollback only covers actions that returned a hash; un-hashable no-op meta updates are skipped, so callers must not assume perfect restoration. Receipts must be collected in apply order — undo replays that order.
**Probe:** `test/server/lib/BundleActions.ts` — `"startUndoBlock commits actions as one undo bundle when finished"` (:54), `"startUndoBlock rollback undoes all applied actions"` (:77).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "startUndoBlock runInUndoBlock", limit: 5 });
```
## Verdict
Adopt the receipts-then-compensate pattern (saga-style) whenever embedding actions in a live-collaboration engine or any store without abort semantics; adapt the receipt type and undo replay call; omit Grist's linkId-clearing specifics but keep a double-stop latch.
