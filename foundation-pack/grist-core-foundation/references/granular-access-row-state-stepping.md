<!-- capsule-v2 -->
# Granular access row-state stepping — how does the engine compute per-row before/after snapshots across a bundle so `rec`/`newRec` predicates and outgoing row filtering stay correct?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How are `rowsBefore`/`rowsAfter` per DocAction computed (including across renames and the whole-bundle `newRec`), and how does the `rec`/`newRec` rule-input convention handle creates and deletes?

## Lazy step computation + related-row snapshot + rec/newRec convention
**Path/Symbol:** `app/server/lib/GranularAccess.ts` — `_getSteps` (:2276-2285), `_getUncachedSteps` (:2287-2358), `_getRowsForRecAndNewRec` (:1886-1915), `_filterRowsAndCells` (:1935-2040); `getRelatedRows` in `app/server/lib/RowAccess.ts` (:18+); `_getRowsBeforeAndAfter` (:1880-1884).
**Signature:** `_getSteps(): Promise<ActionStep[]>` where `ActionStep = { action, rowsBefore, rowsAfter, rowsLast? }`; `_getRowsForRecAndNewRec(cursor): Promise<{rowsBefore, rowsAfter}>`.
**Data Shape:** `rowsBefore`/`rowsAfter` are `TableDataAction` (`["TableData", tableId, rowIds[], colValues]`). `rowsLast` is a cached pointer so `newRec` refers to the END of the whole bundle for the same table, not the immediately-preceding action.

### Decisive source
```ts
// _getUncachedSteps — minimal in-memory DB seeded with the touched rows
const rows = new Map(getRelatedRows(applied ? [...undo].reverse() : docActions));
const docData = new DocData(async (tableId) => ({
  tableData: await this._fetchQueryFromDB({ tableId, filters: { id: [...rows.get(tableId)!] } }),
}), metaData);   // metaData = _grist_Tables + _grist_Tables_column for column types
await Promise.all([...rows.keys()].map(tableId => docData.syncTable(tableId)));
if (applied) { for (const docAction of [...undo].reverse()) { docData.receiveAction(docAction); } }
const steps = [];
for (const docAction of docActions) {
  const tableId = getTableId(docAction);
  const tableData = docData.getTable(tableId);
  const rowsBefore = cloneDeep(tableData?.getTableDataAction() || ["TableData", "", [], {}]);
  docData.receiveAction(docAction);
  const rowsAfter = docData.getTable(tableId) ? cloneDeep(tableData?.getTableDataAction() || ["TableData", "", [], {}]) : rowsBefore;
  steps.push({ action: docAction, rowsBefore, rowsAfter });
}
```
```ts
// _getRowsForRecAndNewRec — newRec points at the LAST row state for the table in the bundle
let tableId = getTableId(rowsBefore); let last = cursor.actionIdx;
for (let i = last + 1; i < steps.length; i++) {
  const act = steps[i].action;
  if (getTableId(act) !== tableId) { continue; }
  if (act[0] === "RenameTable") { tableId = act[2]; continue; }
  last = i;
}
const rowsAfter = steps[cursor.actionIdx].rowsLast = steps[last].rowsAfter;
```

**Flow:** row-state is computed LAZILY (only when rules need it) and ONCE per bundle (`_steps` promise memoized). `getRelatedRows` walks the DocActions tracking renames and newly-added tables to find the minimal set of (tableId, rowIds) touched. A tiny in-memory `DocData` is seeded with those rows plus table/column metadata, the undo actions are replayed if the bundle is already applied, then each DocAction steps the data forward capturing a deep-cloned before/after. For rule predicates, `rec` = rowsBefore and `newRec` = rowsAfter, but for creates `rec`=rowsAfter (no prior state) and for deletes `newRec`=rowsBefore (nothing after) — so a single rule can govern multiple permissions. `newRec` is the LAST state of the table in the bundle, so a rule like `newRec.B <= rec.B` sees the final value even across multiple updates.
**Invariant:** the `rowsLast` cache makes `newRec` bundle-final, not step-local — critical for multi-update bundles. The clone-before-filter discipline (deep clone before censoring) means the shared `_steps` cache is never mutated by outgoing filtering for one client. The TODO warns this is heavy for huge Calculate-all-rows bundles (a full copy per action) — a porter should gate step computation behind "rules exist" (`haveRules()`), as the caller does.
**Probe:** `test/server/lib/GranularAccess.ts` — "respects row-level access control on updates" (:1905, `newRec.B <= rec.B`) and "handles schema changes within a bundle" (:1935, RenameTable swap) pin the rec/newRec and rename-tracking behavior.
**Coverage caveat:** the `rowsLast` bundle-final caching has no dedicated unit test (pinned indirectly by the multi-update suites); the heavy-copy TODO is a documented performance caveat, not a tested contract.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "GranularAccess getSteps getUncachedSteps getRowsForRecAndNewRec rowsLast getRelatedRows", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lazy single-computation + minimal-related-rows snapshot + bundle-final `newRec` + rec/newRec create/delete convention for any rule engine that filters rows by before/after state; adapt the in-memory DocData to your own store; omit the undo-replay branch if your engine never re-applies after commit.
