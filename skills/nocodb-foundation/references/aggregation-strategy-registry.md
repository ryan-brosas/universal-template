<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/index.ts` (41L) + `aggregations/handlers/generic.ts` :28–59 + `aggregations/aggregation-handler.interface.ts` (61L).

# Question
How do you structure per-dialect aggregation SQL generation so adding a dialect never touches shared code?

## Path / Symbol
`AGGREGATION_HANDLER_REGISTRY`, `getAggregationHandler(clientType)`, `GenericAggregationHandler.generate(params)` with the `buildContext → category method → postProcess → wrap` pipeline.

## Signature
```ts
const AGGREGATION_HANDLER_REGISTRY: Partial<Record<ClientType, new () => AggregationHandlerInterface>>
function getAggregationHandler(clientType: ClientType): AggregationHandlerInterface  // index.ts:29
interface AggregationHandlerInterface { generate(params: AggregationGeneratorParams): string | undefined }
```

## Data Shape
Registry maps exactly five ClientTypes: PG, MYSQL, SQLITE, MSSQL, ORACLE. Category methods return `Knex.Raw | undefined`; the final `generate()` returns a fully-wrapped SQL STRING via `.toQuery()`, or `undefined` when the aggregation produced no expression (`none`, unsupported pair).

## Decisive source
index.ts:15–23 — registry is a plain object literal keyed by enum; mssql/oracle entries are CE stub classes whose `generate` **throws** `'MSSQL|ORACLE is only available in the enterprise (EE) build'` (mssql.handler.ts:11–13; comment at index.ts:6 explains the EE build overrides these paths).
generic.ts:28–59 — the four-stage template: (1) abstract `buildContext()` derives dialect inputs; (2) switch on `ctx.aggType ∈ {common,numerical,boolean,date,attachment}` dispatching to category methods whose BASE implementations return `undefined` (=unsupported); (3) `postProcess(ctx, sql)` default no-op, overridden by mssql/oracle to wrap materialized virtual-column aggregates in a scalar subquery; (4) `wrap()`: COALESCE(??, 0) for everything EXCEPT EarliestDate/LatestDate (:109–115), then `?? AS ??` alias if provided (:117–119), then `toQuery()`.
The class doc (:9–24) states the design intent explicitly: "mirrors the field-handler generic/dialect handler split" — subclasses override buildContext + only the categories they implement.

## Flow / Invariant
Three invariants porters get wrong:
1. **undefined ≠ error at this layer** — an unimplemented CATEGORY returns undefined and the caller silently skips that column's selector; but an unregistered DIALECT throws from getAggregationHandler, and an EE-stub dialect THROWS from generate(). Three distinct failure channels.
2. COALESCE-to-0 applies to every aggregation family EXCEPT earliest/latest date — date-range/median/percent all get 0 on empty sets; earliest/latest stay NULL.
3. Alias application happens AFTER COALESCE so the output column keeps the caller's key even when coalesced.

## Probe (direct test)
No upstream spec imports any aggregation handler (recorded gap). From repo root:
```
grep -c 'ClientType\.' packages/nocodb/src/dbQueryClient/aggregations/index.ts     # => 5 registry keys
sed -n '28,59p' packages/nocodb/src/dbQueryClient/aggregations/handlers/generic.ts | grep -c 'case'   # => 5 categories
grep -rn 'only available in the enterprise' packages/nocodb/src/dbQueryClient/aggregations/handlers/ | wc -l   # => 2 (mssql+oracle stubs)
grep -n 'EarliestDate' packages/nocodb/src/dbQueryClient/aggregations/handlers/generic.ts   # => 1 line (:110) gating COALESCE
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"GenericAggregationHandler generate buildContext wrap","limit":3,"detail":"compact"}'
```
→ wrap Method generic.ts 101-122 / generate Method generic.ts 28-59.

## Verdict
**Adopt.** This is the canonical strategy-registry shape for dialect SQL in NocoDB; port it whenever a new aggregation or dialect must slot in without touching orchestration.
