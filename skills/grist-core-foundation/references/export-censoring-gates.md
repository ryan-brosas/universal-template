<!-- capsule-v2 -->
# Export censoring gates — how does an exporter refuse hidden tables without leaking that they exist?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Where exactly do access checks sit in the export pipeline, and what must a porter preserve about the 404-not-403 choice and the doc-level skip?

## Three gates: record lookup, per-table check, whole-doc filter
**Path/Symbol:** `app/server/lib/Export.ts` — `checkTableAccess` (:161–166), the `safe`/`safeTable`/`safeRecord` assertion helpers (:139–159), gate call sites in `doExportTable` (:219), `doExportSection` (:303/:305), and the doc-sweep skip in `doExportDoc` (:180).
**Signature:** `function checkTableAccess(tables: MetaTableData<"_grist_Tables">, tableRef: number): void`.
**Data Shape:** `isTableCensored(tables, tableRef)` (from `app/common/isHiddenTable`) reads `_grist_Tables` metadata rows — censorship is a property of table METADATA, so the check needs no data fetch.

### Decisive source
```ts
// Check that tableRef points to an uncensored table, or throw otherwise.
function checkTableAccess(tables: MetaTableData<"_grist_Tables">, tableRef: number): void {
  if (isTableCensored(tables, tableRef)) {
    throw new ApiError(`Cannot find or access table`, 404);
  }
}
```
And the whole-doc variant:
```ts
const tableRefs = tables.filterRowIds({ summarySourceTable: 0 });
for (const tableRef of tableRefs) {
  if (!isTableCensored(tables, tableRef)) {    // Omit censored tables
    const data = await doExportTable(activeDocSource, { metaTables, tableRef });
    await handleTable(data);
  }
}
```
**Invariant:** the error message is deliberately vague (`Cannot find or access table`) with status **404, not 403** — existence of a censored table is itself secret, so the exporter answers "not found" exactly as it would for a missing table. The section path checks TWICE by construction: `safe(viewSection.tableRef, ...)` (:303) then `checkTableAccess` on the resolved tableRef (:305) — because a section row can point at a table the caller never named. In `doExportDoc` the censored table is SKIPPED silently rather than failing the whole export; one forbidden table must not break the download of the rest.

**Flow:** every entry into table data runs `safeTable(metaTables, "_grist_Tables")` → resolve tableRef (param or `findRow("tableId", …)` with `tableRef === 0 → ApiError(…, 404)`) → `checkTableAccess` → `safeRecord`. `getMetaTables` wraps its fetch in `safe(..., "No metadata available in active document")` so an empty document fails 404 before any per-table logic. Note the asymmetry with `ExportDSV.makeDSVFromTable` (:119–121) which throws `ApiError(\`Table ${tableId} not found.\`, 404)` naming the table when absent — fine there because absence was already proven public-path; the censored case still hides.

**Probe:** deterministic greps (no unit suite drives these paths — coverage caveat):
```bash
cd $REFERENCE_ROOT/grist-core
grep -n "Cannot find or access table" app/server/lib/Export.ts        # 164 (message), 303 (section guard)
grep -n "summarySourceTable: 0" app/server/lib/Export.ts              # 178
grep -rn "export function isTableCensored" app/common/isHiddenTable.ts
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "doExportDoc activeDocSource handleTable", limit: 5 });
// doExportDoc 171-185 carries the skip-loop; checkTableAccess is module-private,
// reached via doExportTable/doExportSection probes.
```

## Verdict
Adopt the 404-veil + silent-skip pair for any multi-tenant bulk export: per-record access errors must be indistinguishable from missing records, and batch operations degrade (skip) instead of aborting. Adapt the censor predicate to your ACL model. Omit nothing here — dropping either half creates either an oracle (leaking hidden names via differential errors) or a denial-of-service handle (one private table kills a teammate's full-doc download).
