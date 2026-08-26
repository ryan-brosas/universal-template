<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts` :60–66 + :42 — `_getListArgs` and the where-string entry.

# Question
How do query-string list args become typed filters before aggregation SQL is composed?

## Path / Symbol
`baseModel._getListArgs(args) → { where, aggregation, ... }`; `extractFilterFromXwhere(context, where, aliasColObjMap) → { filters }`.

## Signature
```ts
const { where, aggregation } = baseModel._getListArgs(args);          // aggregate.ts:42 (same in bulk :62)
const { filters: filterObj } = extractFilterFromXwhere(baseModel.context, where, aliasColObjMap);
```

## Data Shape
args = raw HTTP query (`where` as NocoDB's xwhere mini-language string; `aggregation`/`filterArrJson` as JSON strings the service layer pre-parsed). aliasColObjMap = {title → Column} for resolving xwhere field references.

## Decisive source
aggregate.ts:42 — _getListArgs runs BEFORE column resolution because it also normalizes/validates pagination-ish fields and surfaces `aggregation` used by resolveAggregateColumns downstream (:46–50). The xwhere string parses against aliasColObjMap built from the SAME getColumns call (:44–58), so unknown fields in `where` throw at parse time rather than compiling to broken SQL.
The SDK-owned extractFilterFromXwhere returns a Filter tree consumed by conditionV2 — identical machinery the list endpoint uses, which is why an aggregation request honors exactly the same where-syntax as a data fetch (parity by construction).

## Flow / Invariant
Porter rule: reuse the LIST endpoint's argument parser for the STATS endpoint. Divergent parsers are how "aggregations ignore my filter syntax" bugs are born. The map must come from the same columns snapshot as the aggregation targets or renamed columns slip between parse and compile.

## Probe (direct test)
From repo root:
```
grep -n '_getListArgs' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts   # => 1 + 1 (:42,:62)
grep -n 'getAliasColObjMap' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts                                                                  # => 1 (:55)
grep -n 'extractFilterFromXwhere' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts                                                            # => 2 (:62,:import)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"_getListArgs extractFilterFromXwhere","limit":3,"detail":"compact"}'
```
→ resolves both orchestrations' arg-parsing regions line-exact.

## Verdict
**Adopt.** Shared parser + same-snapshot column map is the parity mechanism; port as-is.
