<!-- capsule-v2 -->
# Granular access check ladder — how does one user action get evaluated from coarse table-level down to per-cell, and how are denied columns/rows stripped or censored?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the full decision ladder from `checkUserActions` to the final per-client filtered DocActions, and what distinguishes a stripped (removed) cell from a censored (sentinel) one?

## Two-pass check + three-way prefilter + outgoing filter
**Path/Symbol:** `app/server/lib/GranularAccess.ts` — `checkUserActions` (:929-952) + `_checkSimpleDataActions` (:1444-1464) + `_checkForSpecialOrSurprisingActions` (:1482-1510) + `_checkAddOrUpdateAccess` (:1527-1558) + `_checkDuplicateTableAccess` (:1585-1618) + `_checkIfNeedsEarlySchemaPermission` (:1560-1578); `_prefilterDocAction` (:2443-2488); `_filterOutgoingDocAction` (:2515-2575); `_filterRowsAndCells` (:1935-2040); `_focusUpdateMemos` (:1695-1706); `_getAccessForActionType` (:2751-2800).
**Signature:** `checkUserActions(docSession, actions: UserAction[]): Promise<void>` (throws on deny); `_prefilterDocAction(cursor): Promise<DocAction[]>`; `_filterOutgoingDocAction(cursor): Promise<ActionCursor[]>`.
**Data Shape:** the five permission props are `read/create/update/delete/schemaEdit` (ALL_PERMISSION_PROPS). `AccessCheck.get(ps)` returns `"allow" | "deny" | "mixed" | "mixedColumns"`; `_focusUpdateMemos` narrows a table-wide denial's memos to the columns the update actually touches (only for the column-granular update permission).

### Decisive source
```ts
// _getAccessForActionType maps a DocAction to its permission class:
if (isMetadataTable(tableId) && tableId !== "_grist_Cells") {
  if (tableId === "_grist_Attachments") { /* rename only; else throw */ }
  if (isAclTable(tableId) && await this.isOwner(docSession)) { return dummyAccessCheck; }
  return accessChecks[severity].schemaEdit;      // metadata needs structure permission
} else if (a[0] === "UpdateRecord" || a[0] === "BulkUpdateRecord") { return accessChecks[severity].update; }
else if (a[0] === "RemoveRecord" || a[0] === "BulkRemoveRecord") { return accessChecks[severity].delete; }
else if (a[0] === "AddRecord" || a[0] === "BulkAddRecord") { return accessChecks[severity].create; }
else { return accessChecks[severity].schemaEdit; }
```
```ts
// _filterRowsAndCells — per-row + per-column, censoring forbidden cells:
for (let idx = 0; idx < rowIds.length; idx++) {
  rec.index = getRecIndex(idx); newRec.index = getNewRecIndex(idx);
  const rowPermInfo = new PermissionInfo(ruler.ruleCollection, input);
  const rowAccess = rowPermInfo.getTableAccess(tableId);   // per-record: evaluates all column rules
  const access = accessCheck.get(this._focusUpdateMemos(action, rowAccess, rowPermInfo, tableId));
  if (access === "deny") { toRemove.push(idx); }
  else if (access !== "allow" && colValues) {
    for (const colId of Object.keys(colValues)) {
      const colAccess = rowPermInfo.getColumnAccess(tableId, colId);
      if (accessCheck.get(colAccess) === "deny") { censorAt(colId, idx); censoredRows.add(idx); }
    }
  }
}
```

**Flow:** `checkUserActions` runs five coarse pre-engine passes (simple data actions at table level; special/surprising action allowlists; AddOrUpdateRecord requires full read + update + create; DuplicateTable requires full read + schemaEdit; early schema permission when Python formulas could run) — these catch read-exposing actions that DocActions alone can't reveal, and reject before the engine mutates. After the engine produces DocActions, `_prefilterDocAction` (only for the ApplyUndoActions partial-fulfillment path) strips forbidden material; `_checkIncomingDocAction` (fatal) throws on any denial for direct actions; `_filterOutgoingDocAction` rewrites each client's view: deny→drop the whole action, mixedColumns→`_pruneColumns` (delete denied columns, null if nothing left), mixed→`_pruneRows` (remove denied rows, and for newly-allowed rows synthesize AddRecords so the client's cache converges) + censor cells with `[GristObjCode.Censored]`.
**Invariant:** a forbidden ROW is removed; a forbidden CELL is CENSORED (replaced with the `Censored` sentinel) — the distinction is load-bearing because the client must know the row exists but the value is hidden. `allowRowRemoval:false` (used when filtering OUTGOING) throws "Unexpected row removal" if a non-remove action would drop a row, forcing the caller to rewrite instead. The `_focusUpdateMemos` scoping is what makes a table-wide denial report the touched column's reason, not a shadowed lower-precedence rule's remedy.
**Probe:** `test/server/lib/GranularAccess.ts` — "respects row-level access control" (:1826) + "on updates" (:1905) pin row filtering with `rec`/`newRec` predicates; "scopes memos to the touched column when a table-wide update is denied" (:1057) pins `_focusUpdateMemos`; "respects owner-private tables" (:780) + "hides transform columns from users without SCHEMA_EDIT" (:477) pin metadata/schema gates.
**Coverage caveat:** the `mixedColumns` clone path has no dedicated unit test (exercised via the suites); `_checkIfNeedsEarlySchemaPermission`'s Python-formula branch is covered by "blocks formulas early" (:1445).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "GranularAccess checkUserActions prefilterDocAction filterOutgoingDocAction focusUpdateMemos", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-pass (coarse pre-engine + definitive post-engine) check ladder, the remove-vs-censor row/cell split, and the `_focusUpdateMemos` scoping for any ACL engine over an action log; adapt the permission prop set and rule source; omit the ApplyUndoActions partial-fulfillment prefilter if your undo is all-or-nothing.
