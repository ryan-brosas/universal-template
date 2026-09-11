<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts` (whole, 184L).

# Question
How do you compute the same aggregates for N different filter sets in ONE query — without letting one malformed bucket silently run unfiltered?

## Path / Symbol
`bulkAggregate(client, logger?) → (context, ctx: BulkAggregateCtx) => Promise<Record<alias, Record<string, unknown>>>`

## Signature
`bulkFilterList: Array<{ alias: string; where?: string; filterArrJson?: string | Filter[] }>` — each entry becomes one JSON-packed selector column.

## Decisive source
bulk-aggregate.ts:33–46 — **filterArrJson validation happens BEFORE the try block**: `parseFilterArrJson(context, f.filterArrJson, 'bulk-aggregate bucket "${f.alias}"')` per bucket, keyed by alias in a Map. The comment pins the reason: the try's catch swallows errors into `{}`, so a malformed filter parsed inside would be silently dropped "which would run the aggregation UNFILTERED" — an authorization-adjacent data-leak class. Validation outside ⇒ malformed filter surfaces as a 400.
:96–171 — per bucket: fresh tQb; SIX stacked filter groups (RLS, view-root when viewId, args.filterArr, top-level where via extractFilterFromXwhere called AGAIN inline :125–129, the bucket's own aggFilter from f.where, optional parsedFilterArrJson); soft-delete appended (:150–153).
:157–166 — expressions generated PER SET with `baseQuery: tQb` — the comment names it the "Phase 2 correctness invariant": median/attachment-size materialize over the FILTERED rows, not the table.
:168–170 — `client.bulkAggregateRowSelector(baseModel, tQb, expressions, f.alias)` packs the set; selectors all ride ONE outer query (`qb.select(...selectors); qb.limit(1)` :173–174).
Catch swallows into `{}` (:180–183) — AFTER up-front validation has already moved user-input errors out of its reach.

## Flow / Invariant
The two invariants that porters get wrong: (1) validate-then-swallow ordering (user input errors are 400s; runtime failures are empty objects); (2) every aggregate expression must be generated against THAT bucket's filtered builder — sharing one expression string across buckets computes every bucket over the first bucket's filters.

## Probe (direct test)
From repo root:
```
sed -n '31,47p' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts | grep -c 'parseFilterArrJson'   # => 1 call site before try
grep -n 'Phase 2 correctness' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts                    # => 1 (:156)
grep -c 'new Filter' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts                             # => 6 groups (:91 RLS conditional + :113 view-filter + :119 filterArr + :124 xwhere + :133 aggFilter + :140 per-set JSON filters)
grep -n 'qb.limit(1)' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts                            # => 1 (:174)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"bulkAggregate orchestration parsedFilterArrJsonByAlias","limit":2,"detail":"compact"}'
```
→ resolves the generic.ts delegation + orchestration family.

## Verdict
**Adopt.** The N-buckets-one-query shape with per-set expression generation is the reusable widget-footer contract; keep validation OUTSIDE the swallowing catch.
