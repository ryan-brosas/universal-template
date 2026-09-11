<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :278–353 (numerical) + mysql.handler.ts :276–360 + sqlite.handler.ts :274–388.

# Question
How does the Rating column's zero-as-empty rule thread through every numerical aggregate without breaking the other numeric columns?

## Path / Symbol
`PgAggregationHandler.numerical / MysqlAggregationHandler.numerical / SqliteAggregationHandler.numerical` — Rating branches inside Avg/Min/StdDev/Range.

## Signature
```ts
// Rating Avg (pg FILTER form):  AVG((??)) FILTER (WHERE (??) != 0)
// mysql/sqlite CASE form:       AVG(CASE WHEN (??) != 0 THEN (??) ELSE NULL END)
```

## Data Shape
condnValue=0 for Rating (set in each buildContext); non-Rating numeric columns take the plain aggregate with NO filter — NULLs already excluded by SQL semantics.

## Decisive source
pg.handler.ts:325–334 — Range comment is the parity keystone: "FILTER binds to the immediately preceding aggregate, so this is MAX(all) - (MIN(...) FILTER (WHERE ... != 0)). Intentional: Rating treats 0 as 'empty' for Min/Range but counts it for Max — matches the JS reducer in nocodb-sdk/aggregationCompute.ts." So on a rating column Max INCLUDES zeros while Min EXCLUDES them; range = max(all) − min(nonzero).
pg StdDev (:314–322): `stddev_pop(...) FILTER (WHERE != 0)` — population stddev, not sample.
mysql (:284–291/:297–306/:310–318): identical rules re-expressed as CASE WHEN...ELSE NULL (no FILTER clause in MySQL) — ELSE NULL matters because AVG/MIN/STDDEV ignore NULL rows.
sqlite StdDev (:315–350): hand-rolled SQRT(SUM((x−avg)²)/COUNT(*)) where the rating predicate `(??) IS NOT NULL AND (??) != 0` must be injected into BOTH the inner avg subquery AND the outer variance scan via filterBindings spread — missing either copy computes variance against an avg that counted zeros.
Sum has NO rating branch anywhere — summing zeros is a no-op, deliberately unfiltered.

## Flow / Invariant
Porter traps: (1) zero-exclusion is PER-FUNCTION not per-column — Sum/Max stay unfiltered even for Rating; (2) the pg FILTER clause binds only to the adjacent aggregate, so multi-aggregate expressions need one FILTER per aggregate (the Range SQL is the worked example); (3) stddev is POPULATION everywhere and hand-rolled on sqlite.

## Probe (direct test)
From repo root:
```
grep -c 'FILTER (WHERE (??) != ??)' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts   # => 4 (Avg :287, Min :301, Stddev :317, Range-inner-Min :331)
grep -n 'aggregationCompute' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts         # => 1 (:329 JS-reducer parity note)
grep -c 'ELSE NULL END' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts           # => 4 (Avg/Min/Stddev rating arms + Range's Min)
grep -c 'stddev_pop' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts                 # => 2 (Rating + plain)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"numerical Rating FILTER stddev_pop","limit":3,"detail":"compact"}'
```
→ resolves the three numerical methods line-exact.

## Verdict
**Adapt.** Port the per-function zero-rule matrix and keep the SDK-reducer parity comment attached to whichever file lands in your port.
