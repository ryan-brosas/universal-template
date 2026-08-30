<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts` :109–126 vs `bulk-aggregate.ts` :109–171 — parallel vs sequential selector generation.

# Question
Why does single aggregation build its selectors under Promise.all while bulk builds them in a for-loop?

## Path / Symbol
`aggregate()`'s `await Promise.all(aggregateColumns.map(async ...))`; `bulkAggregate()`'s `for (const f of bulkFilterList) { ... for (const {col, agg} of aggregateColumns) { await applyAggregation(...) } }`.

## Signature
Both push `Knex.Raw` selectors into a shared array before a single `qb.select(...selectors)`.

## Data Shape
Single: N columns × 1 filter set, all expressions independent → concurrent applyAggregation calls (each may hit getColumnNameQuery/DB for virtual-column compilation).
Bulk: M buckets × N columns; the INNER loop stays sequential per bucket, and bucket tQbs are built one at a time.

## Decisive source
aggregate.ts:107–120 — Promise.all over per-column closures pushing into `selectors[]` — safe because each closure touches only its own column and array push order is irrelevant (aliases key results). The concurrency pays off where virtual columns compile via DB round-trips.
bulk-aggregate.ts:96–171 — deliberately sequential: each iteration CLONES and mutates a fresh tQb (:97), generates that bucket's expressions against it (:157–166), then consumes it immediately inside bulkAggregateRowSelector (:168–170) which SELECTs on the same builder object. Parallelizing would either share one mutable tQb across buckets or multiply open queries; knex builders are single-use-ish once selects attach.
Also: single-mode reuses ONE qb for filters AND select (:60/:126); bulk-mode keeps an outer qb (:80) separate from per-bucket tQbs — two different query topologies.

## Flow / Invariant
Porter rule: expression GENERATION is I/O (virtual-column compilation) and parallelizes by column; expression CONSUMPTION binds to a specific builder instance and serializes. Collapsing both loops into Promise.all deadlocks or cross-contaminates buckets.

## Probe (direct test)
From repo root:
```
grep -n 'Promise.all' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts    # => 1 (:109)
grep -n 'for (const f of bulkFilterList)' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts   # => 1 (:96)
grep -c 'const tQb = baseModel.dbDriver' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts    # => 1 (:97 fresh builder per bucket)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"Promise.all aggregateColumns selectors","limit":2,"detail":"compact"}'
```
→ resolves the aggregate.ts fan-out region line-exact.

## Verdict
**Adopt.** Concurrency topology is part of the contract here, not an implementation detail.
