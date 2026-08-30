<!-- capsule-v2 -->
# Search-index two-pass resolution — hit rows then ROW_NUMBER over the live view

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does "which row number is my search hit in the CURRENT view" survive filtering/sorting that SQL can't express in one pass?

## Pass 1 search ids → Pass 2 ROW_NUMBER() OVER () position query
**Path/Symbol:** `apps/nestjs-backend/src/features/aggregation/aggregation.service.ts:getRecordIndexBySearchOrder` (:912–1117) — take-cap :931–941, projection intersection :951–955, pass-1 `searchIndexQuery` :1011–1021, exact-match mode :1045–1058, pass-2 CTEs :1060–1077, NaN guard :1085–1093; non-search twin `getRecordIndex` (:1146–1183); index builder `db-provider/postgres.provider.ts:searchIndexQuery` (:633–655).
**Signature:** `getRecordIndexBySearchOrder(tableId, ISearchIndexByQueryRo, projection?) → {index, fieldId, recordId}[] | null`.
**Data Shape:** pass-1 rows `{__id, fieldId}`; pass-2 rows `{row_num, __id}`; response index is 1-based in exact-match mode (baseSkip + acc length), 0-based in `getRecordIndex` (`row_num - 1`).

### Decisive source
```ts
const indexQueryBuilder = this.knex
  .with('t', viewRecordsQB.from({ [alias]: viewCte || dbTableName }))
  .with('t1', (db) => {
    db.select('__id').select(this.knex.raw('ROW_NUMBER() OVER () as row_num')).from('t');
  })
  .select('t1.row_num').select('t1.__id').from('t1')
  .whereIn('t1.__id', [...new Set(recordIds.map((record) => record.__id))]);
...
const index = Number(indexResultMap[item.__id]?.row_num);
if (isNaN(index)) {
  throw new CustomHttpException('Index not found', HttpErrorCode.NOT_FOUND, ...);
}
```

**Flow:** Pass 1 runs the trgm/full-text search (bounded by statement_timeout) returning matching record ids + which field matched. Exact-match mode (`search[2]`) skips positioning entirely and reports running indices. Otherwise pass 2 re-derives THE VIEW's ordered record sequence (buildFilterSortQuery with skip/take stripped) as CTE `t`, numbers it with `ROW_NUMBER() OVER ()` into `t1`, then looks up each hit id. A hit whose id vanished from the view mid-flight → Number(undefined) = NaN → 404 Index not found.
**Invariant:** `OVER ()` with NO PARTITION/ORDER means numbering follows `t`'s materialized order — so `t` MUST already carry the view's full ORDER BY; adding an ORDER BY to t1 or reusing a stale page would silently misnumber. The NaN check is the race guard for delete-between-passes: fail loud rather than report a wrong scroll position. The 1000-take cap (:931) exists because pass-2's whereIn list rides the same statement.
**Probe:** `grep -cF 'ROW_NUMBER() OVER ()' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getRecordIndexBySearchOrder ROW_NUMBER row_num whereIn", limit: 10 });
```

## Verdict
Adopt two-pass id-then-position when positions depend on app-level ordering; keep the unnumbered-OVER contract explicit; adapt the miss policy (404 vs skip).
