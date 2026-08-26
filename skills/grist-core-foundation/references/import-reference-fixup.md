<!-- capsule-v2 -->
# Import reference fixup — how do Ref columns survive table renames between parse time and import time?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Parsed data references target tables by ORIGINAL names, but AddTable sanitizes table ids — how do references get rewired without corrupting cell data?

## Encode refs as Int at parse, stage everything in hidden tables, then ModifyColumn to the REAL sanitized Ref type afterwards
**Path/Symbol:** `app/server/lib/ActiveDocImport.ts`: `_encodeReferenceAsInt` (619–631), `_fixReferences` (636–664), hidden-table staging loop `importParsedFileAsNewTable` (234–317, esp. BulkAddRecord-not-ReplaceTable comment :271–274), `cleanColumnMetadata` Any-type guessing + DateTime timezone conversion (709–736).
**Signature:** `_encodeReferenceAsInt(parsedTables): ReferenceDescription[]` where descriptor = `{tableIndex, colIndex, refTableId}`; `_fixReferences(docSession, tables, fixedColumnIdsByTable, references, isHidden)`.
**Data Shape:** `ReferenceDescription[]` captures WHERE each ref column lives BY INDEX before any id changes; final type string `` `Ref:${sanitizedHiddenTableId}` ``.

### Decisive source
```ts
const refTableId = gutil.removePrefix(col.type, "Ref:");
if (refTableId) { references.push({ refTableId, colIndex, tableIndex }); col.type = "Int"; }
...
// after ALL tables exist under their sanitized ids:
const fixedTableId = tables[ref.tableIndex].hiddenTableId;
userActions.push(["ModifyColumn", fixedTableId,
  fixedColumnIds[fixedTableId][ref.colIndex],
  { type: `Ref:${tablesByOrigName[ref.refTableId].hiddenTableId}` }]);
if (isHidden) { // mirror the retarget onto the transform-rule helper columns too
  userActions = userActions.concat(userActions.map(([, t, c, info]) =>
    ["ModifyColumn", t, IMPORT_TRANSFORM_COLUMN_PREFIX + c, info]));
}
```

**Flow:** parser output declares `Ref:<origName>` columns → all such columns are downgraded to plain Int (raw row ids preserved losslessly) while their positions/namesakes are recorded → every parsed sheet is staged into its own hidden table via AddTable (ids now SANITIZED, possibly ≠ original names) with data loaded via BulkAddRecord so Any-column type guessing still applies ("Don't use parseStrings, only use the strict parsing in ValueGuesser to make the import lossless") → only after every table exists do the recorded Int columns get retyped to point at the sanitized targets. Self-references work because lookup goes through `tablesByOrigName`.
**Invariant:** you cannot declare `Ref:` during AddTable because the target's final id isn't known until ITS AddTable returns — order of operations is load-as-int THEN retype; skipping the encode step yields broken/blank references whenever sanitization renames anything. The hidden-mode duplication of fixups keeps GenImporterView's transform columns consistent with the visible ones.
**Probe:** exercised via doc-worker import suites incl. multi-sheet xlsx with cross-table references (`test/server/lib/ImportBridge.ts`); no direct unit test of `_fixReferences` at this pin — caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "_fixReferences _encodeReferenceAsInt ModifyColumn Ref importParsedFileAsNewTable", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any ETL that must preserve relational columns across identifier normalization: defer relationship typing until all entities exist under final ids, carrying raw keys meanwhile. Adapt the two-phase typing to your schema API (ALTER TYPE instead of ModifyColumn). Omit the transform-column mirroring when you have no importer-preview twin columns.
