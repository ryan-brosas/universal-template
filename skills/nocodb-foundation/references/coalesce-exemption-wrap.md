<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/generic.ts` :100–122 (`wrap`) + `pg.handler.ts` :397–410 vs `mysql.handler.ts` :405–416.

# Question
Which aggregations are allowed to return NULL, and how is the alias applied relative to COALESCE?

## Path / Symbol
`GenericAggregationHandler.wrap(ctx, aggregationSql)` — the shared output stage every category SQL passes through.

## Signature
```ts
protected wrap(ctx: AggregationSqlContext, aggregationSql: Knex.Raw): string | undefined {
  if (![AllAggregations.EarliestDate, AllAggregations.LatestDate].includes(aggregation as any))
    result = knex.raw(`COALESCE(??, 0)`, [result]);
  if (alias) result = knex.raw(`?? AS ??`, [result, alias]);
  return result?.toQuery();
}
```

## Data Shape
Output string: `COALESCE(<aggregate>, 0) AS <colId>` — or bare `<aggregate> AS <colId>` for the two date exemptions; no-alias calls (bulk path binds alias at the row-selector instead) skip the AS stage.

## Decisive source
generic.ts:109–115 — the exemption list is EXACTLY two names (EarliestDate, LatestDate). Everything else coalesces to 0: empty-set SUM/AVG (SQL NULL), zero-row COUNT denominators via NULLIF already inside percent SQL, and even DateRange/MonthRange (empty ⇒ 0 days/months rather than NULL).
:117–119 — alias AFTER coalesce so the projected column name survives the wrap; alias is `col.id` in single mode (see aggregate-filter-stack-order) and bucket alias in bulk mode.
DateRange recipes confirm intent: pg MAX::date − MIN::date over empty set is NULL → coalesced to 0 by THIS stage, not in the handler (:406–410).

## Flow / Invariant
Porter trap: adding a new aggregation whose empty-result SHOULD be NULL requires editing THIS list — the category methods cannot express it. The wrap is also why no handler SQL contains its own COALESCE except attachment-size's inner sum belt-and-suspenders (attachment-size-json-array-sum): outer wrap owns null-safety uniformly.

## Probe (direct test)
From repo root:
```
sed -n '101,122p' packages/nocodb/src/dbQueryClient/aggregations/handlers/generic.ts | grep -c 'COALESCE\|AS ??'   # => 2
grep -n 'EarliestDate' packages/nocodb/src/dbQueryClient/aggregations/handlers/generic.ts                          # => 1 (:110)
grep -rn 'COALESCE' packages/nocodb/src/dbQueryClient/aggregations/handlers/*.handler.ts | grep -v generic | wc -l  # => 1 (pg attachment inner)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"GenericAggregationHandler wrap","limit":2,"detail":"compact"}'
```
→ `...generic.GenericAggregationHandler.wrap Method ... generic.ts 101-122`.

## Verdict
**Adopt.** Single-stage null/alias normalization with a named exemption list is the cleanest part of the whole plane — port verbatim.
