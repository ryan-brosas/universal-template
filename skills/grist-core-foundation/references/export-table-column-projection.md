<!-- capsule-v2 -->
# doExportTable column projection — how does a table export decide which columns exist, what they are named, and which formatter renders each cell?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the exact pipeline from metadata rows to the per-column `ExportColumn` list, and which metadata field wins at each decision (visibility, display column, label, order)?

## Metadata-driven projection: hide helpers, substitute display columns, keep outer labels
**Path/Symbol:** `app/server/lib/Export.ts` inside `doExportTable` (:199–273) — column selection + ordering (:222–225), projection map with display-column substitution (:228–242), formatter construction via `createFullFormatterFromDocData(docData, tc.id)` from `app/common/ValueFormatter` (ValueFormatter.ts:314–329).
**Signature:** `doExportTable(activeDocSource: ActiveDocSource, options: { metaTables?, tableRef?, tableId? }): Promise<ExportData>`.
**Data Shape:** `ExportColumn { id, colId, label, type, formatter, parentPos, description }`; `access: Access[]` built as `columns.map(col => getters.getColGetter(col.id)!)` — note accessors are keyed by the PROJECTED `id` (displayCol's), not the original column's.

### Decisive source
```ts
// Select only columns that belong to this table.
const tableColumns = metaColumns.filterRecords({ parentId: tableRef })
  // sort by parentPos and id, which should be the same order as in raw data
  .sort((c1, c2) => nativeCompare(c1.parentPos, c2.parentPos) || nativeCompare(c1.id, c2.id));

const columns: ExportColumn[] = tableColumns
  .filter(tc => !gristTypes.isHiddenCol(tc.colId))    // Exclude helpers
  .map<ExportColumn>((tc) => {
  // for reference columns, return display column, and copy settings from visible column
    const displayCol = metaColumns.getRecord(tc.displayCol) || tc;
    return {
      id: displayCol.id,
      colId: displayCol.colId,
      label: tc.label,                    // OUTER column's label survives substitution
      type: tc.type,                      // OUTER column's type drives formatting family
      formatter: createFullFormatterFromDocData(docData, tc.id),   // OUTER colRef → full formatter chain
      parentPos: tc.parentPos,
      description: tc.description,
    };
  });
```
**Invariant:** three different columns contribute to ONE exported column: identity comes from the **display column** (`displayCol.id`/`colId` — so Reference cells export their shown value's coordinates), while presentation (`label`, `type`) stays from the **outer visible column**. The formatter is built from `tc.id` (the outer column ref) because `createFullFormatterFromDocData` resolves the reference-formatting chain internally (it pulls `visibleColType`/`visibleColWidgetOpts` out of widgetOpts and composes the display-column formatter — ValueFormatter.ts:319–335). Drop the fallback `|| tc` and every plain column whose `displayCol` field is 0 crashes; drop `isHiddenCol` and `manualSort`/aux helper columns leak into every download.

**Flow:** `_grist_Tables_column.filterRecords({parentId})` → sort by `(parentPos, id)` = physical raw-data order → filter hidden helpers → project with display substitution → `fetchTable(table.tableId)` → `ServerColumnGetters(rowIds, dataByColId, columns)` → `getters.getColGetter(col.id)` per projected column. Table name borrows the primary view's name when one exists (`table.primaryViewId` → `_grist_Views.name`, :253–260) — exports show friendly names, ids stay internal. Doc settings ride along (`docSettings`) because formatters consult document defaults.

**Probe:** deterministic greps (coverage caveat: no dedicated unit file):
```bash
cd $REFERENCE_ROOT/grist-core
grep -n "filterRecords({ parentId: tableRef })" app/server/lib/Export.ts   # 223
grep -n "metaColumns.getRecord(tc.displayCol) || tc" app/server/lib/Export.ts  # 232
grep -n "createFullFormatterFromDocData(docData, tc.id)" app/server/lib/Export.ts  # 238
grep -n "export function createFullFormatterFromDocData" app/common/ValueFormatter.ts  # 314
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "doExportSection", limit: 5 });
// sibling function shares viewify(); for the table path use:
//   search_graph({query:"doExportTable metaColumns", ...}) → Export.doExportTable Function 199-273
```

## Verdict
Adopt this projection shape whenever exporting relational rows with user-facing semantics: visibility filter FIRST, then display-value substitution with outer-presentation preservation, then format resolution against the OUTER column. Adapt the hidden-column predicate to your schema. Omit the primary-view rename only if your UI has no per-table display names — but keep the substitution triple intact; splitting it is the classic porter error that exports raw rowids instead of labels.
