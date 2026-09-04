<!-- capsule-v2 -->
# doExportSection viewify + filter precedence — how does a section export reproduce exactly what the user sees, including unsaved UI filters and display columns?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** In what order do filter sources override each other, how do sort specs get rewritten onto display columns, and what does the row pipeline look like end-to-end?

## WYSIWYG projection: unsaved filters beat saved filters; sorts are re-pointed at display columns before any data flows
**Path/Symbol:** `app/server/lib/Export.ts` inside `doExportSection` (:291–397) — index-by-colRef maps (:314–316), `viewify` (:319–330), `buildFilters` (:331–340), `columnsForFilters` vs `viewColumns` split (:341–345), sort-spec rewrite (:347–361), fetch→sort→AND-filter→link-filter pipeline (:363–383).
**Signature:** `doExportSection(activeDocSource, viewSectionId, sortSpec: Sort.SortSpec | null, filters: Filter[] | null, linkingFilter: FilterColValues | null, { metaTables? }): Promise<ExportData>` with `Filter = { colRef: number, filter: string }`.
**Data Shape:** THREE colRef-keyed maps: `fieldsByColRef` (which columns the view shows), `savedFiltersByColRef` (persisted `_grist_Filters` rows), `unsavedFiltersByColRef` (request-body filters from the UI). `viewColumns` order comes from `_grist_Views_section_field.parentPos`, NOT table column order.

### Decisive source
```ts
const filterString = unsavedFiltersByColRef[col.id]?.filter || savedFiltersByColRef[col.id]?.filter;
```
```ts
// The columns named in sort order need to now become display columns
sortSpec = sortSpec || gutil.safeJsonParse(viewSection.sortColRefs, []);
sortSpec = sortSpec!.map((colSpec) => {
  const colRef = Sort.getColRef(colSpec);
  if (typeof colRef !== "number") {
    // colRef might be string for virtual tables, but we don't support them here.
    throw new Error(`Unsupported colRef type: ${typeof colRef}`);
  }
  const col = metaColumns.getRecord(colRef);
  if (!col) {
    return 0;                                   // vanished column degrades to no-op spec
  }
  const effectiveColRef = viewify(col, fieldsByColRef[colRef]).id;   // → display column ref
  return Sort.swapColRef(colSpec, effectiveColRef);
});
```
**Invariant:** filter precedence is **unsaved (live UI state) > saved (persisted per-section) > none**, resolved PER COLUMN via `||` — a porter who merges these globally instead of per-column changes what "export current view" means mid-session. Sort rewriting happens BEFORE fetching: sorting a Reference column must compare displayed values, so each spec's colRef is swapped to its display column (`Sort.swapColRef` preserves direction and extras by rebuilding the spec — SortSpec.ts:212–218). A deleted column in the spec becomes `0` (dropped by the sorter) instead of throwing. Virtual-table string colRefs are explicitly unsupported here and throw.

**Flow:** resolve section → censor-check its table → build `columnsForFilters` from ALL non-hidden table columns (filters may reference hidden-in-view columns) → build `viewColumns` only from the section's fields via `viewify` (display-col substitution identical to doExportTable, but formatter gets `field?.id` too so per-FIELD format overrides apply: :326) → fetch raw table once (`fetchTable(table.tableId)`) → `ServerColumnGetters` + `SortFunc.compare` in-place `rowIds.sort(...)` → fold every per-column predicate into ONE conjunctive rowFilter (`reduce((prev,cur)=> id => prev(id)&&cur(id), ()=>true)`) → apply saved+unsaved → then `getLinkingFilterFunc(getters, linkingFilter)` for cross-section linked filtering. Exported `access`/`columns` use ONLY `viewColumns` (:393–394) — filtered-but-hidden columns influence WHICH rows export, never which columns.

**Probe:** deterministic greps (coverage caveat: no dedicated unit file):
```bash
cd $REFERENCE_ROOT/grist-core
grep -n "unsavedFiltersByColRef\[col.id\]?.filter || savedFiltersByColRef" app/server/lib/Export.ts  # 332
grep -n "Sort.swapColRef(colSpec, effectiveColRef)" app/server/lib/Export.ts  # 360
grep -n "prevFilter(id) && curFilter(id)" app/server/lib/Export.ts  # 377
grep -n "getLinkingFilterFunc(getters, linkingFilter)" app/server/lib/Export.ts  # 382
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "doExportSection", limit: 5 });
// → grist-core.app.server.lib.Export.doExportSection Function app/server/lib/Export.ts 291-397
```

## Verdict
Adopt this whole shape for any "export/share exactly my current view" feature: per-column three-source filter resolution, pre-fetch display-column sort rewrite with graceful degradation, single AND-folded pass over one fetched table, and a hard separation between row-selection columns and projected columns. Adapt the linking filter to your cross-widget selection model; omit it if you have no linked views. The precedence ladder is the invariant most porters get wrong — encode it as data flow, not as an afterthought.
