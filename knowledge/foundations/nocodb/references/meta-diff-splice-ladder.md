<!-- capsule-v2 -->
# Three-way splice diff — how do you diff DB schema vs stored metadata without double-reporting, and why does splice order matter?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When meta-sync compares live introspection against NocoDB's column metadata, what exact algorithm produces TABLE_COLUMN_ADD / TYPE_CHANGE / REMOVE without duplicates?

## MetaDiffsService.getMetaDiff (table/column phase)
**Path/Symbol:** `packages/nocodb/src/services/meta-diffs.service.ts:getMetaDiff` (:163-839); type vocabulary `MetaDiffType` (:40-56); apply-order constant (:58-61).
**Signature:** `async getMetaDiff(context, sqlClient, base, source): Promise<Array<MetaDiff>>` where MetaDiff = `{table_name, source_id, type: ModelTypes, detectedChanges: MetaDiffChange[]}`.
**Data Shape:** Per table: iterate `colListRef[tn]` (DB columns) against `oldMeta.columns` (stored), MUTATING both arrays via findIndex+splice — matched columns are REMOVED from the stored list as they're matched.

### Decisive source
```ts
for (const column of colListRef[table.tn]) {
  const oldColIdx = oldMeta.columns.findIndex((c) => c.column_name === column.cn);
  // new table  [sic — new COLUMN]
  if (oldColIdx === -1) {
    tableProp.detectedChanges.push({ type: MetaDiffType.TABLE_COLUMN_ADD, msg: `New column(${column.cn})`, cn: column.cn, id: oldMeta.id });
    continue;
  }
  const [oldCol] = oldMeta.columns.splice(oldColIdx, 1);   // consumed: can't fire twice

  if (
    oldCol.dt !== column.dt ||
    // if mysql and data type is set or enum then compare dtxp as well
    (['mysql', 'mysql2'].includes(source.type) && ['set','enum'].includes(column.dt) && column.dtxp !== oldCol.dtxp) ||
    // PG native enum: dt stays 'USER-DEFINED' but option list can change via ALTER TYPE ADD/RENAME VALUE,
    // or the underlying enum type itself can be swapped (different udt_name).
    (source.type === 'pg' && column.udt_typtype === 'e' &&
      (column.dtxp !== oldCol.dtxp || column.data_type_custom !== oldCol.internal_meta?.pg_enum_type_name))
  ) { /* TABLE_COLUMN_TYPE_CHANGE */ }
  if (detectColumnSchemaPropsChanged(oldCol, column)) { /* TABLE_COLUMN_PROPS_CHANGED */ }
}
// whatever REMAINS in oldMeta.columns was never matched by a DB column:
for (const column of oldMeta.columns) {
  if ([LinkToAnotherRecord, Links, Rollup, Lookup, Formula, QrCode, Barcode, Button].includes(column.uidt) ||
      isAIPromptCol(column) ||
      // skip alias columns of CreatedTime, LastModifiedTime, CreatedBy, LastModifiedBy
      ([CreatedTime, LastModifiedTime, LastModifiedBy, CreatedBy].includes(column.uidt) && !column.system)) continue;
  tableProp.detectedChanges.push({ type: MetaDiffType.TABLE_COLUMN_REMOVE, ... });
}
```

**Flow:** skip `source.isMeta()` → hint `sqlClient.bulkColumnList = true` (Oracle N+1 batching; "no-op for clients that don't implement it") → tableList (+relationListAll once per source) → per table: NEW (no stored meta) | splice-diff columns → leftover stored tables ⇒ TABLE_REMOVE → virtual-relation pass over collected LTAR columns → views repeat the same ladder (VIEW_NEW/VIEW_COLUMN_*/VIEW_REMOVE). Type-change comparison is dialect-aware THREE ways: base `dt` inequality; mysql set/enum must also compare dtxp; PG native enums compare dtxp AND udt_name because dt stays 'USER-DEFINED'.
**Invariant:** The same Column object may legitimately produce BOTH a TYPE_CHANGE and a PROPS_CHANGED entry (two independent ifs, no else). Virtual/system columns must be excluded from COLUMN_REMOVE or every sync would delete computed fields. `nc_evolutions` table and base-prefix filtering (`t.tn?.startsWith(base?.prefix)` when meta source) are hard-coded exclusions.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `MetaDiffsService.getMetaDiff` :163-839 exactly; grep confirms one `bulkColumnList` assignment and two splice-diff ladders (tables :269-321 + views :752-792).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getMetaDiff TABLE_COLUMN_TYPE_CHANGE splice", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the consume-on-match splice diff (it makes ADD/CHANGE/REMOVE mutually exclusive by construction), dialect-gated type comparison, and the virtual-column remove exemption. Adapt MetaDiffType names to your change taxonomy. Omit view-phase duplication by parameterizing the ladder if your host has one model kind.
