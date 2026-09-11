<!-- capsule-v2 -->
# Related-row pre-existing tracking — how does Grist compute the minimal set of pre-existing rows a bundle of DocActions may touch, discounting rows minted inside the bundle and tracking table renames?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** When the ACL engine needs to snapshot rows before applying a bundle, how does it find which (tableId, rowId) pairs are pre-existing and could be touched, without including rows created within the same bundle?

## Pre-existing-row tracker with minted-row discount + rename/added-table tracking
**Path/Symbol:** `app/server/lib/RowAccess.ts` — `getRelatedRows` (:18-66), `RowIdTracker` (:8-12); consumed by `GranularAccess._getUncachedSteps` (`app/server/lib/GranularAccess.ts` :2311) and `GranularAccess._getRowsForRecAndNewRec` path (:1398).
**Signature:** `getRelatedRows(docActions: DocAction[]): readonly (readonly [string, Set<number>])[]` — returns `[tableId, Set<rowId>]` pairs keyed by the PRE-EXISTING table id.
**Data Shape:** `RowIdTracker = { blockedIds: Set<number> (ids minted within the bundle), blocked: boolean (all pre-existing rows wiped), ids: Set<number> (pre-existing rows touched) }`. Output is a list of `[tableId, Set<rowId>]` where `tableId` is the table's name BEFORE any renames in the bundle.

### Decisive source
```ts
const tableIds = new Map<string, string>();      // key is current tableId
const rowIds = new Map<string, RowIdTracker>();  // key is pre-existing tableId
const addedTables = new Set<string>();
for (const docAction of docActions) {
  const currentTableId = getTableId(docAction);
  const tableId = tableIds.get(currentTableId) || currentTableId;
  if (docAction[0] === "RenameTable") {
    if (addedTables.has(currentTableId)) { addedTables.delete(currentTableId); addedTables.add(docAction[2]); continue; }
    tableIds.delete(currentTableId); tableIds.set(docAction[2], tableId); continue;
  }
  if (docAction[0] === "AddTable") { addedTables.add(currentTableId); }
  if (docAction[0] === "RemoveTable") { addedTables.delete(currentTableId); continue; }
  if (addedTables.has(currentTableId)) { continue; }
  const tracker = getSetMapValue(rowIds, tableId, () => new RowIdTracker());
  if (docAction[0] === "RemoveRecord" || docAction[0] === "BulkRemoveRecord" ||
    docAction[0] === "UpdateRecord" || docAction[0] === "BulkUpdateRecord") {
    if (!tracker.blocked) {
      for (const id of getRowIdsFromDocAction(docAction)) {
        if (!tracker.blockedIds.has(id)) { tracker.ids.add(id); }
      }
    }
  } else if (docAction[0] === "AddRecord" || docAction[0] === "BulkAddRecord") {
    for (const id of getRowIdsFromDocAction(docAction)) { tracker.blockedIds.add(id); }
  } else if (docAction[0] === "ReplaceTableData" || docAction[0] === "TableData") {
    tracker.blocked = true;
  }
}
return [...rowIds.entries()].map(([tableId, tracker]) => [tableId, tracker.ids] as const);
```

**Flow:** walk the bundle once. `tableIds` maps each current table id back to its pre-rename name; `addedTables` marks tables created within the bundle (their rows are all internal). Renames on an added table just move the added marker; renames on a pre-existing table remap the pre-existing name. For each data action: adds mint the row ids into `blockedIds` (so a later update/remove of that same id is NOT counted as pre-existing); updates/removes add their row ids to `ids` unless `blocked` (a prior `ReplaceTableData`/`TableData` wiped all pre-existing rows for that table) or the id was minted in-bundle; `ReplaceTableData`/`TableData` set `blocked`. The result maps each pre-existing table name to the set of pre-existing row ids the bundle touches.
**Invariant:** the returned table key is the table's name BEFORE the bundle's renames — consumers must resolve it against the pre-action schema. Rows added and then updated/removed within the same bundle are never reported as pre-existing. A `ReplaceTableData`/`TableData` marks the whole table blocked (no pre-existing row can be referred to from then on). Newly added tables are skipped entirely (their rows are internal).
**Probe:** `test/server/lib/RowAccess.ts` — "accumulates individual updates and removes" (:8), "accumulates bulk updates and removes" (:22), "discounts rows added within the bundle" (:43), "discounts replacement rows" (:54), "tolerate table renames" (:61), "ignore new tables" (:73), "keep table names straight" (:81).
**Coverage caveat:** the `blocked` flag interaction with a rename-then-replace sequence is covered only by the rename/replacement suites together; no single test isolates `blocked` + `blockedIds` interplay.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "getRelatedRows RowIdTracker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pre-existing-row tracker with minted-row discount, the pre-rename table-name keying, the added-table skip, and the `ReplaceTableData`/`TableData` blocked-flag; adapt to your own action vocabulary (the four record-action kinds + replace); omit nothing — this is a self-contained reusable primitive for any "which rows could a mutation touch" pre-snapshot.
