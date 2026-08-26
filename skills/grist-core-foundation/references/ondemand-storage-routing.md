<!-- capsule-v2 -->
# On-demand table storage routing — how do you decide which tables bypass the in-memory engine and hit SQLite directly, and which indexes must exist for that to stay fast?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you route UserActions to an alternate storage for flagged tables and derive the exact index set the alternate storage needs?

## Metadata-table-driven predicate + derived Ref-column index wish-list
**Path/Symbol:** `app/server/lib/OnDemandActions.ts:OnDemandActions` (class :12–47; `isOnDemand` :23–28; `getDesiredIndexes` :37–46); base class `AlternateActions` (app/common/AlternateActions.ts) converts UserActions→DocActions+undo.
**Signature:** `class OnDemandActions extends AlternateActions { constructor(_storage: OnDemandStorage, _docData: DocData, _forceOnDemand = false); isOnDemand(tableId): boolean; usesAlternateStorage(tableId): boolean; getDesiredIndexes(): IndexColumns[] }`.
**Data Shape:** reads live meta tables `_grist_Tables` (`tableId`, `onDemand`) and `_grist_Tables_column` (`parentId`, `colId`, `type`); returns `{ tableId, colId }[]`.

### Decisive source
```ts
public isOnDemand(tableId: string): boolean {
  if (this._forceOnDemand) { return true; }
  const tableRef = this._tablesMeta.findRow("tableId", tableId);
  // OnDemand tables must have a record in the _grist_Tables metadata table.
  return tableRef ? Boolean(this._tablesMeta.getValue(tableRef, "onDemand")) : false;
}

public getDesiredIndexes(): IndexColumns[] {
  const desiredIndexes: IndexColumns[] = [];
  for (const c of this._columnsMeta.getRecords()) {
    const t = this._tablesMeta.getRecord(c.parentId as number);
    if (t && t.onDemand && c.type && (c.type as string).startsWith("Ref:")) {
      desiredIndexes.push({ tableId: t.tableId as string, colId: c.colId as string });
    }
  }
  return desiredIndexes;
}
```

**Flow:** every action for a table first asks `usesAlternateStorage(tableId)` → `_forceOnDemand` short-circuits true (test/edge mode), else a linear `findRow` over `_grist_Tables` decides from the row's `onDemand` flag; unknown tables are NOT on-demand (missing record ⇒ false). Independently, `getDesiredIndexes` walks all column records, resolves each column's parent table, and emits one index per Reference-typed column of an on-demand table — because lookups/filters against those tables filter by ref columns.
**Invariant:** The flag lives in the METADATA table, not config: flipping `onDemand` via a normal UpdateRecord immediately reroutes storage with no restart. A missing meta row means "regular" (fail toward the engine path, not the alternate). Index derivation must stay in lockstep with the predicate — both read the same two meta tables, so a ported version that hardcodes table lists will drift. Consumers use the returned indexes to CREATE INDEX IF NOT EXISTS on the SQLite side.
**Probe:** `test/server/lib/OnDemandActions.ts` — real ActiveDoc with a table flipped via `["UpdateRecord", "_grist_Tables", tableRef, { onDemand: true }]`: `"should create correct (Bulk)UpdateRecord"` (:85), `"should create correct (Bulk)AddRecord"` (:112), `"should create correct (Bulk)RemoveRecord"` (:133), and `"should handle actions bigger than maxSQLiteVariables"` (:152, N=1723 rows through the alternate path incl. undo round-trips).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "OnDemandActions isOnDemand getDesiredIndexes AlternateActions", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape "storage route decided by a metadata flag row + index wish-list derived from the same metadata" for any hybrid engine/direct-SQL store. Adapt the trigger column type (here `Ref:` prefix) to your foreign-key encoding, and replace the linear findRow with a real index if your table count is large (upstream TODO says exactly this). Omit `_forceOnDemand` unless you need whole-doc test modes.
