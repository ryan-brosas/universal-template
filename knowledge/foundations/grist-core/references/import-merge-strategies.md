<!-- capsule-v2 -->
# Import merge strategies — how do you reconcile imported rows into an existing table without a full diff engine?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Given source (hidden) and destination tables matched on merge columns, what are the exact merge semantics per strategy, and how are matched/unmatched rows turned into user actions?

## Three pure MergeFunctions + one SQL comparison query feeding BulkUpdate/BulkAdd; skipped columns pin destination values
**Path/Symbol:** `app/server/lib/ActiveDocImport.ts`: `getMergeFunction` (682–699), `_mergeAndFinishImport` (484–570), `generateImportDiff` preview twin (136–214), `_getTableComparison` → `buildComparisonQuery` (587–601), `IMPORT_TRANSFORM_COLUMN_PREFIX` mapping (28, 449–450), `stripPrefixes` (668–671).
**Signature:** `type MergeFunction = (srcVal: CellValue, destVal: CellValue) => CellValue`; `_mergeAndFinishImport(docSession, hiddenTableId, destTableId, {destCols, sourceCols}, {mergeCols, mergeStrategy})`.
**Data Shape:** strategies: `replace-with-nonblank-source` | `replace-all-fields` | `replace-blank-fields-only`; comparison result is a columnar map keyed `"table.col"` with parallel arrays.

### Decisive source
```ts
case "replace-with-nonblank-source": return (srcVal, destVal) => isBlankValue(srcVal) ? destVal : srcVal;
case "replace-all-fields":           return (srcVal, _destVal) => srcVal;
case "replace-blank-fields-only":    return (srcVal, destVal) => isBlankValue(destVal) ? srcVal : destVal;
default: { const unknownStrategyType: never = type; throw new Error(`Unknown merge strategy: ...`); }

// row reconciliation over the SQL-matched join:
if (comparisonResult[destTableId + ".id"][i] === null) {
  matchingDestColIds.forEach(id => newRecords[id].push(comparisonResult[`${hiddenTableId}.${srcColId}`][i]));
  numNewRecords++;
} else {
  updatedRecords[id].push(merge(srcVal, destVal));
  updateRecordIds.push(comparisonResult[destTableId + ".id"][i]);
}
// single batch at the end:
actions = [["RemoveTable", hiddenTableId], ["BulkUpdateRecord",...], ["BulkAddRecord",...]];
await applyUserActions(docSession, actions, { parseStrings: true });
```

**Flow:** client merge col ids arrive prefixed (`gristHelper_Import_`) and are stripped → `buildComparisonQuery` LEFT-JOINs destination onto source deduped via MIN(id)-GROUP-BY (see existing comparison-query-dedup-join capsule) → each joined row is classified unmatched→add vs matched→update → per-cell merge function resolves conflicts → hidden table removed and BOTH bulk actions applied in ONE call so they land in one undo step. The PREVIEW path (`generateImportDiff`) reuses the identical comparison but emits an ActionSummary with `[before, after]` pairs, treating added rows as updates of blank→value, and pins SKIPPED columns (blank formula) to the DESTINATION value.
**Invariant:** merge functions are total over (src,dest) including nulls — blankness uses `isBlankValue`, not truthiness; unknown strategy throws (never silently defaults); `parseStrings` differs by path (true for merges into existing typed columns, false for into-new-table imports so ValueGuesser keeps imports lossless). Source-column resolution rule: `$colId` formulas map to real source columns; anything else reads the synthetic `gristHelper_Import_<destColId>` column GenImporterView created.
**Probe:** exercised through importer suites (`test/server/lib/ImportBridge.ts` / doc-worker import tests drive both strategies end-to-end); direct unit test of getMergeFunction absent at this pin — caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "getMergeFunction mergeAndFinishImport generateImportDiff buildComparisonQuery", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-strategy vocabulary verbatim for CSV/sheet merge UX (it maps exactly to "keep mine/theirs/fill blanks") and the classify-then-batch action emission. Adapt the SQL comparison to your storage (any OUTER JOIN on natural keys works). Omit the ActionSummary preview shape unless you need a review UI.
