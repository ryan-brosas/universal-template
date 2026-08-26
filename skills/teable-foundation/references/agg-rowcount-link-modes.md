<!-- capsule-v2 -->
# Row-count link-cell modes — candidate vs selected vs restricted id sets

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does one row-count endpoint serve plain views, "add link record" pickers, and cell-level "selected records" chips without three codepaths?

## handleRowCount's restrictRecordIds split + whereIn/whereNotIn polarity
**Path/Symbol:** `apps/nestjs-backend/src/features/aggregation/aggregation.service.ts:performRowCount` (:503–545) + `handleRowCount` (:555–653) — restrict computation :582–583, keepPrimaryKey :587, count alias injection :597–608, polarity :629–647.
**Signature:** `performRowCount(tableId, IRowCountRo) → {rowCount: number}`.
**Data Shape:** IRowCountRo carries `filterLinkCellCandidate?`, `filterLinkCellSelected?`, `selectedRecordIds?`; SQL always `COUNT(*)::int AS count`.

### Decisive source
```ts
const restrictRecordIds =
  selectedRecordIds && !filterLinkCellCandidate ? selectedRecordIds : undefined;
...
if (selectedRecordIds) {
  filterLinkCellCandidate
    ? qb.whereNotIn(`${alias}.__id`, selectedRecordIds)
    : qb.whereIn(`${alias}.__id`, selectedRecordIds);
}
if (filterLinkCellCandidate) {
  await this.recordService.buildLinkCandidateQuery(qb, tableId, filterLinkCellCandidate);
}
if (filterLinkCellSelected) {
  await this.recordService.buildLinkSelectedQuery(qb, tableId, dbTableName, alias, filterLinkCellSelected);
}
```

**Flow:** Plain view → view CTE + optional search/filter. Link-cell CANDIDATE mode ("records you could still add"): selected ids become a whereNOTIn EXCLUSION (already-linked rows drop out of candidates). SELECTED mode ("records currently linked"): keepPrimaryKey preserves the link field through the permission wrap and buildLinkSelectedQuery joins the junction side; selected ids ride inside that builder. Restricted mode (plain selection stats): ids go straight into the aggregate builder as whereIn.
**Invariant:** The `&& !filterLinkCellCandidate` guard at :582 is the crux — in candidate mode the SAME list means "already linked" (exclusions), not "only these" (restrictions); passing it as restrictRecordIds would invert the picker's semantics. Count uses the synthetic `{fieldId:'*', statisticFunc: Count, alias:'count'}` aggregation-field shape so it rides the identical permission/CTE pipeline as real statistics — no bespoke COUNT query to forget RLS on. Porters who bypass wrapView for "just a count" leak soft-deleted/hidden rows.
**Probe:** `grep -cF 'whereNotIn' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 1; `grep -cF "statisticFunc: StatisticsFunc.Count" apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "handleRowCount buildLinkCandidateQuery restrictRecordIds", limit: 10 });
```

## Verdict
Adopt one counting spine with mode-specific id-set polarity; adapt candidate/selected builders to your link storage; never special-case the permission wrap away.
