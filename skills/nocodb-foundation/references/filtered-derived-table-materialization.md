<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts` :17–74 (buildContext) + sqlite.handler.ts :17–74 (identical shape).

# Question
How do filtered-aggregate subqueries (median, std_dev, attachment size) honor the caller's row filters on engines without FILTER clauses?

## Path / Symbol
`MysqlAggregationHandler.buildContext` / `SqliteAggregationHandler.buildContext` → `subAggFrom`, `subAggCol`, `derivedInner`.

## Signature
```ts
const derivedInner = baseQuery
  ? baseQuery.clone().clearSelect().select(knex.raw(`(??) as nc_val`, [column_query]))
  : undefined;
const subAggFrom: string | Knex.Raw = derivedInner ? knex.raw(`(??) as nc_agg_sub`, [derivedInner]) : baseModelSqlv2.tnPath;
const subAggCol: string | Knex.QueryBuilder = derivedInner ? 'nc_val' : column_query;
```

## Data Shape
A filtered derived table `((SELECT ..., (col_expr) AS nc_val FROM ... WHERE <caller filters>) AS nc_agg_sub)` becomes the FROM source for self-contained-subquery aggregates; the column inside it is the fixed name `nc_val`.

## Decisive source
mysql.handler.ts:29–44 / sqlite.handler.ts identical (:29–44): when a baseQuery was supplied, median/stddev/attachment-size run `FROM (filtered-derived) nc_agg_sub` selecting `nc_val`; WITHOUT a baseQuery they fall back to raw table + inline column expression. The comment states the invariant: "so they honor filters; falls back to the raw table only when no baseQuery was supplied. (Inline aggregates keep using column_query over the outer query.)"
Consumer — attachment size mysql.handler.ts:437–439: `(SELECT SUM(JSON_EXTRACT(json_object,'$.size')) FROM ?? CROSS JOIN JSON_TABLE(CAST(?? AS JSON),'$[*]' ...) )` bound to `[subAggFrom, subAggCol]`; sqlite twin :463–466 uses `json_each`.
Median mysql.handler.ts:333–353 binds `[subAggCol, subAggCol, subAggFrom, subAggCol]` into a ROW_NUMBER window over the derived table.

## Flow / Invariant
The invariant that breaks silently if missed: **a scalar-subquery aggregate is a SEPARATE query** — it cannot see the outer query's WHERE. Any dialect lacking FILTER/CASE-over-window support must re-materialize the filter set by embedding the caller's own (already-filtered) QueryBuilder as the FROM clause. `clearSelect()` before adding nc_val is load-bearing: keeping the caller's select list would break DISTINCT/GROUP BY-free semantics and bloat the derived table.

## Probe (direct test)
From repo root:
```
grep -c 'nc_agg_sub' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts   # => 1 per file
grep -c 'clearSelect' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts  # => 1 per dialect file (mysql+sqlite)
sed -n '336,352p' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts | grep -c 'nc_med' # => 8 (val/rn/cnt/q naming family)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"SqliteAggregationHandler","limit":3,"detail":"compact"}'
```
→ common/numerical/boolean/date Methods sqlite.handler.ts 76-272/274-388/390-424/426-455 (buildContext resolved via MysqlAggregationHandler.buildContext 17-74 twin).

## Verdict
**Adopt.** The derived-table materialization pattern ports to any engine where aggregates can't reference outer-query filters; keep the no-baseQuery fallback so ad-hoc column stats still work.
