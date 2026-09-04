<!-- capsule-v2 -->
# TQL pipe + view-merge param funnel — how REST filters compose with saved views

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do filterByTql, custom filter, and the saved view's own filter combine before SQL compilation?

## Pipe converts; service merges via mergeWithDefaultFilter
**Path/Symbol:** pipe `apps/nestjs-backend/src/features/record/open-api/tql.pipe.ts` (:7–24); controller wiring `aggregation-open-api.controller.ts:107` (`ZodValidationPipe(aggregationRoSchema), TqlPipe`); merge sites `aggregation.service.ts:buildStatisticsData` (:744–753) and `getCalendarDailyCollection` :1265–1267; ignoreViewQuery switches (:42, :519, :875, :925).
**Signature:** `transform(value: {filterByTql?, filter?})` mutating in place; `mergeWithDefaultFilter(viewFilterJson, customFilter)` from @teable/core.
**Data Shape:** IFilter conjunction tree; view filter stored as JSON string column.

### Decisive source
```ts
if (value.filterByTql) {
  try {
    value.filter = parseTQL(value.filterByTql);
  } catch (e) {
    throw new BadRequestException(`TQL parse error, ${(e as Error).message}`);
  }
}
// aggregation.service.ts
if (viewRaw?.filter || withView?.customFilter) {
  const filter = mergeWithDefaultFilter(viewRaw?.filter, withView?.customFilter);
```

**Flow:** Zod validates the raw query shape FIRST, then TqlPipe rewrites `filterByTql` into a structured `filter` (parse errors → 400 with the parser message). Downstream, the resolved view row's persisted filter JSON merges with the caller's custom filter (AND-composition per core's merge helper); sort follows the same recipe where "caller's orderBy overrides view.sort". Every read endpoint exposes `ignoreViewQuery` which simply drops viewId — and with it view filter/sort/columnMeta — for raw-table statistics.
**Invariant:** The pipe MUTATES the query object rather than cloning — safe only because it runs inside the request pipeline before anyone else reads it. Merge order is semantic: the VIEW filter is the base scope (what the user sees), custom filters narrow it; a porter who lets custom REPLACE view filters turns "show me overdue rows of my filtered view" into a different table. ignoreViewQuery must bypass BOTH filter AND sort AND statisticFunc columnMeta together — half-bypassing yields footer stats computed over invisible rows.
**Probe:** `grep -cF 'parseTQL' apps/nestjs-backend/src/features/record/open-api/tql.pipe.ts` → 2; `grep -cF 'mergeWithDefaultFilter' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TqlPipe parseTQL mergeWithDefaultFilter", limit: 10 });
```

## Verdict
Adopt validate→convert→merge funnels for view-scoped reads; adapt TQL to your filter DSL; keep ignore-semantics all-or-nothing.
