<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts` :333–353 + `sqlite.handler.ts` :367–381 — the two non-pg median recipes.

# Question
How do MySQL and SQLite compute a true median without percentile functions, and where does each break?

## Path / Symbol
NumericalAggregations.Median per handler.

## Signature
```sql
-- mysql 8:  SELECT AVG(nc_med_val) FROM (
--            SELECT (x) AS nc_med_val, ROW_NUMBER() OVER (ORDER BY (x)) AS nc_med_rn, COUNT(*) OVER () AS nc_med_cnt
--            FROM <subAggFrom> WHERE (x) IS NOT NULL ) nc_med_q
--           WHERE nc_med_rn IN (FLOOR((nc_med_cnt+1)/2), FLOOR((nc_med_cnt+2)/2))
-- sqlite:   (SELECT AVG((x)) FROM (SELECT (x) FROM <subAggFrom> WHERE (x) IS NOT NULL
--            ORDER BY (x) LIMIT 2 - (SELECT COUNT(x) FROM src) % 2 OFFSET (SELECT (COUNT(x)-1)/2 FROM src)))
```

## Data Shape
Both average the middle TWO values when N is even (FLOOR((N+1)/2)∪FLOOR((N+2)/2) hit one value when odd, two when even) — standard interpolated-median parity with pg's percentile_cont(0.5).

## Decisive source
mysql.handler.ts:336–353 — window-function form bound to [subAggCol×2, subAggFrom, subAggCol]; requires MySQL ≥8.0 (comment :334). The subAggFrom/subAggCol indirection means it reads from the FILTERED derived table — without baseQuery the raw table path keeps filters honored only via outer query (see filtered-derived-table-materialization).
sqlite.handler.ts:369–381 — LIMIT/OFFSET arithmetic: `LIMIT 2 - (COUNT % 2) OFFSET ((COUNT-1)/2)` picks 1 row (odd) or 2 rows (even) after ordering; nine binds because subAggCol appears in five positions and subAggFrom in three. The comment-free triple-subquery on COUNT re-scans the set twice — O(n log n) sort plus two counts; fine for view footers, a trap at warehouse scale.
Both exclude NULLs pre-order (`WHERE IS NOT NULL`) so positions index only real values.

## Flow / Invariant
Porter traps: (1) even-N averaging must include BOTH middle rows — an integer-position-only port returns a biased low-middle; (2) sqlite's OFFSET math is 0-based over the NON-NULL subset only — applying it to unfiltered counts shifts every median; (3) mysql's version silently fails below 8.0 (ROW_NUMBER unknown) — pin your engine floor.

## Probe (direct test)
From repo root:
```
grep -c 'nc_med_rn' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts   # => 2 (:342 def + :347 use)
grep -c 'nc_med' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts      # => 8 (val/rn/cnt/q family)
grep -n 'LIMIT 2' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts    # => 1 (:369)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"Median ROW_NUMBER FLOOR LIMIT OFFSET","limit":3,"detail":"compact"}'
```
→ resolves both median recipes line-exact.

## Verdict
**Adapt.** Port either recipe to engines lacking percentile_cont; keep the even-N averaging contract exact.
