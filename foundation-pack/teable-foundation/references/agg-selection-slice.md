<!-- capsule-v2 -->
# Selection aggregation slice — skip/take over the grid's exact visible sequence

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the selection-chip endpoint aggregate ONLY the selected row range while staying byte-compatible with the grid's ordering?

## Collapsed-group filter + group-prefixed sort + forced table path
**Path/Symbol:** `apps/nestjs-backend/src/features/aggregation/open-api/aggregation-open-api.service.ts:getSelectionAggregation` (:140–222, design comment :140–155); slice plumbing `aggregation.service.ts:performAggregation` (:111–205, `isPaginated` :144–148); forced-table-path guard `record-query-builder.service.ts:246–250`.
**Signature:** `getSelectionAggregation(tableId, ISelectionAggregationRo)` → same `IAggregationVo` as footer aggregation.
**Data Shape:** request carries `skip/take/orderBy/collapsedGroupIds/groupBy`; BASE CTE = rows `[skip, skip+take)` of filtered+sorted output.

### Decisive source
```ts
const sortWithGroup = [...(groupBy ?? []), ...(orderBy ?? [])];
// collapsedGroupIds -> SQL filter via getGroupRelatedData so the slice indexes
// the same visible-record sequence the grid renders
...
await this.aggregationService.performAggregation({
  tableId, withView,
  // useQueryModel must stay false here: the tableCache path skips BASE CTE
  // pagination, which would silently aggregate the entire view.
  useQueryModel: false,
  skip, take,
  orderBy: sortWithGroup.length ? sortWithGroup : undefined,
});
```

**Flow:** (1) groupBy is folded INTO orderBy as a sort prefix and NOT passed via withView — two documented reasons: `performGroupedAggregation` keys by fieldId so multi-func chips would lose entries, and it re-runs handleAggregation un-sliced computing whole-view group totals. (2) collapsedGroupIds translate into a SQL filter through `recordService.getGroupRelatedData`'s collapsed-filter builder so hidden groups never occupy the [skip,take) window. (3) In the query builder, `usePaginatedRange = limit !== undefined` forces `effectiveUseQueryModel=false` and `paginationMode:'full'`, emitting the BASE_<alias> CTE with limit+offset applied server-side.
**Invariant:** The slice is only correct if sort ≡ grid order: records list sorts `[...groupBy, ...orderBy]` and this mirrors it; drop the group prefix and take/skip indexes a different sequence than the user sees. The useQueryModel:false force is load-bearing in BOTH layers — the service comment AND the builder's `usePaginatedRange ? false : useQueryModel` — because the tableCache model has no BASE pagination and would aggregate everything silently (no error!). defaultOrderField (view's row-order column or __auto_number) supplies the deterministic tiebreaker.
**Probe:** `grep -cF 'usePaginatedRange ? false : useQueryModel' apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts` → 1; `grep -cF 'sortWithGroup' apps/nestjs-backend/src/features/aggregation/open-api/aggregation-open-api.service.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getSelectionAggregation skip take collapsedGroupIds", limit: 10 });
```

## Verdict
Adopt slice-scoped aggregates by wrapping pagination INSIDE the base CTE, never on the outer aggregate; adapt the collapsed-group filter to your grouping model.
