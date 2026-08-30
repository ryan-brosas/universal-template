<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `pg.handler.ts` :324–353 (Range/Median), `mysql.handler.ts` :333–354 (Median), `sqlite.handler.ts` :315–382 (StdDev/Median), `sqlite.ts` :22–35 + `mysql.ts` :28–48 + `pg.ts` :24–38 (row selectors).

# Question
How is a percentile-50 computed identically across three engines — and how are N per-set aggregates packed into one row?

## Path / Symbol
`NumericalAggregations.Median` per handler; `PGDBQueryClient/MySqlDBQueryClient/SqliteDBQueryClient.bulkAggregateRowSelector`.

## Signature
```ts
// mysql 8 window median (over subAggFrom/subAggCol):
SELECT AVG(nc_med_val) FROM (
  SELECT (??) AS nc_med_val, ROW_NUMBER() OVER (ORDER BY (??)) AS nc_med_rn, COUNT(*) OVER () AS nc_med_cnt
  FROM ?? WHERE (??) IS NOT NULL
) nc_med_q WHERE nc_med_rn IN (FLOOR((nc_med_cnt+1)/2), FLOOR((nc_med_cnt+2)/2))
// pg:    percentile_cont(0.5) within group (order by (??))
// sqlite: LIMIT/OFFSET pair-average over ordered non-null values
```

## Data Shape
bulkAggregateRowSelector returns `Knex.Raw` of `( <tQb with one JSON column> ) as <alias>` — the derived-table row selector that bulkAggregate unions into its outer SELECT.

## Decisive source
pg.handler.ts:342–347 — `percentile_cont(0.5) within group (order by ...)`; the Rating Range case (:325–334) carries the load-bearing comment: "FILTER binds to the immediately preceding aggregate, so this is MAX(all) - (MIN(...) FILTER (...)). Intentional: Rating treats 0 as empty for Min/Range but counts it for Max — matches the JS reducer in nocodb-sdk/aggregationCompute.ts." That asymmetry (MAX unfiltered, MIN filtered) is the parity contract with the SDK's client-side reducer.
sqlite.handler.ts:315–353 — std_dev has NO native function: hand-rolled SQRT(SUM((x-avg)^2)/COUNT(*)) over a double-nested derived table, alias bound mid-expression (`AS ??`, :329), rating filter duplicated into BOTH avg and value subqueries via filterBindings spread (:339–349).
Row selectors: pg `JSON_BUILD_OBJECT('id', expr,...)` wrapped `(??) as ??` (pg.ts:31–37); mysql `JSON_UNQUOTE(JSON_OBJECT(...))` PLUS `.limit(1)` on tQb — mysql.ts:39–46 documents both the regression (bare JSON_OBJECT once rode the UNFILTERED outer query so per-bucket filters were silently ignored on MySQL) and the limit(1) requirement ("median/attachment-size are non-aggregate scalar subqueries... without it → 'subquery returns more than 1 row'"); sqlite plain `json_object(...)` (sqlite.ts:29–34).

## Flow / Invariant
Porter traps: (1) MySQL's selector MUST limit(1) or every bucket with a scalar-subquery aggregate explodes; (2) JSON key order follows Object.keys(expressions) insertion = aggregateColumns order = view column order; (3) execAndParse({bulkAggregate:true}) then JSON.parses each `{...}` string (BaseModelSqlv2.ts:7302+/:7389) — selectors must emit STRING JSON (hence JSON_UNQUOTE on mysql) for that contract.

## Probe (direct test)
From repo root:
```
grep -n 'percentile_cont' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts          # => 1 (:344)
grep -c 'FILTER (WHERE' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts           # => 24 FILTER clauses
grep -c 'limit(1)' packages/nocodb/src/dbQueryClient/mysql.ts                                            # => 2 (:43 comment + :46 call — grep -c counts LINES, both carry the token)
sed -n '321,350p' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts | grep -c 'SQRT\|avg_value\|subAggCol'   # => 6 (stddev recipe family incl. bindings)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"MysqlAggregationHandler numerical median ROW_NUMBER","limit":2,"detail":"compact"}'
```
→ `...mysql.handler.MysqlAggregationHandler.numerical ... mysql.handler.ts 276-360`.

## Verdict
**Adapt.** Port the per-engine median/stddev recipes and the three JSON packers as-is; preserve the mysql limit(1) and the Rating max/min filter asymmetry exactly.
