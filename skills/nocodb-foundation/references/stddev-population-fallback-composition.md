<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :314–340 vs `sqlite.handler.ts` :315–366 — StdDev/Range dialect pairing.

# Question
Which numerical aggregates have NO native function on some engine, and how does the fallback preserve population-statistics semantics?

## Path / Symbol
StandardDeviation on sqlite (hand-rolled) vs pg stddev_pop vs mysql STDDEV; Range everywhere as MAX−MIN composition.

## Data Shape
Population (÷N) stddev everywhere — never sample (÷N−1). sqlite's two-level derived table computes avg first, then Σ(x−avg)²/N inside SQRT.

## Decisive source
sqlite.handler.ts:315–353 — the hand-rolled form: outer `SQRT(SUM(((x)-avg_value)*((x)-avg_value))/COUNT(*))` over an inner SELECT carrying `(x), (SELECT AVG(x) FROM src WHERE filter) AS avg_value FROM src WHERE filter`. The alias binding `AS ??` (:329, bound to col.id/alias param) exists ONLY because sqlite needs a column name for the derived table — pg/mysql need none. Rating filterBindings spread appears TWICE (:346,:348 — inner avg AND outer scan must both exclude zeros).
pg.handler.ts:314–322 — `stddev_pop((x)) FILTER (...)` — native population function + FILTER arm for rating.
Range: no dedicated function anywhere; always composed MAX−MIN with the Rating Min-filtered/Max-unfiltered asymmetry (pg :325–334 carries the parity comment).
COUNT(*)>0 CASE guard (:324–328) returns NULL instead of SQRT(NULL) garbage on empty sets — then wrap()'s COALESCE makes it 0 like every other numeric.

## Flow / Invariant
Porter rule: when your target lacks a native population-stddev, port sqlite's exact shape INCLUDING the double-filter injection and the empty-set NULL guard; a sample-stddev or single-filter variant silently changes every reported deviation and NaNs on empty sets.

## Probe (direct test)
From repo root:
```
grep -n 'stddev_pop\|STDDEV' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts   # => 2 + 2 lines
grep -c 'avg_value' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts    # => 2 (definition :333 + use :326)
sed -n '324,328p' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts | grep -c 'WHEN COUNT'  # => 1 empty-set guard
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"stddev SQRT avg_value","limit":3,"detail":"compact"}'
```
→ resolves both stddev implementations line-exact.

## Verdict
**Adapt.** Port per-engine: native pop-stddev where it exists, the guarded two-level composition where it doesn't.
