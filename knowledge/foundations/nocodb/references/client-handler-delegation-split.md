<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/generic.ts` :205–230 (`generateAggregateQuery` + `aggregate` + `bulkAggregate` delegations).

# Question
Why did the dialect clients STOP overriding generateAggregateQuery, and what does the base-class delegation buy?

## Path / Symbol
`GenericDBQueryClient.generateAggregateQuery(params)` → `getAggregationHandler(this.clientType).generate(params)`; `aggregate(context, ctx)` → `aggregateOrchestration(this)(context, ctx)`; `bulkAggregate` → `bulkAggregateOrchestration(this)`.

## Signature
```ts
generateAggregateQuery(params: AggregationGeneratorParams): string | undefined {
  return getAggregationHandler(this.clientType).generate(params);   // generic.ts:212–216
}
```

## Data Shape
Three delegations compose two strategy layers: the CLIENT (dialect identity) and the HANDLER (aggregation SQL), plus one ORCHESTRATION closure per public method.

## Decisive source
generic.ts:205–211 — the doc comment records the migration explicitly: "Resolves the per-dialect aggregation strategy from the registry... **the aggregation analogue of the field-handler dispatch. Subclasses no longer override this**; instead each dialect ships an AggregationHandler class." Before this shape, five client classes each carried a copy of every aggregation switch.
generic.ts:218–223 / :225–230 — aggregate/bulkAggregate delegate to closures that take the CLIENT as their first argument (`aggregateOrchestration(this)`) — curried so the shared orchestration stays importable/testable without subclass context while still dispatching dialect-specific row packing through `client.bulkAggregateRowSelector`.
The consequence: adding a dialect = one client class (identity + micro-abstractions + row selector) + one handler class (buildContext + category methods) + one registry line. NOTHING in cross-db-utils changes.

## Flow / Invariant
Layer discipline for porters: orchestration (cross-db-utils) → prelude (applyAggregation) → strategy (aggregations/handlers) → client micro-SQL (pg.ts etc.). Each layer may only call the one below. The curried-closure style is what keeps orchestrations free of class state — port it as plain functions taking the client interface.

## Probe (direct test)
From repo root:
```
sed -n '205,216p' packages/nocodb/src/dbQueryClient/generic.ts | grep -c 'getAggregationHandler'   # => 1
grep -n 'no longer override this' packages/nocodb/src/dbQueryClient/generic.ts                     # => 1 (:209)
grep -rn 'generateAggregateQuery' packages/nocodb/src/dbQueryClient/pg.ts packages/nocodb/src/dbQueryClient/mysql.ts packages/nocodb/src/dbQueryClient/sqlite.ts | wc -l   # => 0 overrides in dialect clients
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"GenericDBQueryClient generateAggregateQuery getAggregationHandler","limit":2,"detail":"compact"}'
```
→ resolves the delegation block line-exact.

## Verdict
**Adopt.** The two-layer strategy split (client × handler) with registry resolution is the reusable architecture kernel of this entire plane.
