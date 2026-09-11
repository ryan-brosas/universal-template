<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/mssql.ts` (34L), `oracle.ts` (44L), `aggregations/handlers/mssql.handler.ts` + `oracle.handler.ts` (14L each), `cross-db-utils/single-query-cache.ts` (30L).

# Question
How does the CE build stub EE-only dialects so imports resolve and failures are loud and uniform?

## Path / Symbol
`MssqlDBQueryClient`, `OracleDBQueryClient`, `MssqlAggregationHandler`, `OracleAggregationHandler`, `SINGLE_QUERY_DEFAULT_VIEW`, `singleQueryCacheKey`.

## Signature
```ts
class MssqlDBQueryClient extends GenericDBQueryClient {
  private static readonly EE_ONLY = 'MSSQL is only available in the enterprise (EE) build';
  concat/_simpleCast/bulkAggregateRowSelector: throw new Error(EE_ONLY)
}
```

## Decisive source
mssql.ts:11–12 / oracle.ts:12–13 — one shared static message string per class; every stubbed method throws THE SAME Error instance-text, so logs dedupe cleanly. Oracle additionally overrides batchUpdate (:27–34) because batch-pk-update is implemented for pg/mysql/sqlite/mssql in CE but NOT oracle.
aggregations/index.ts:6 — the comment explains the resolution trick: "mssql / oracle resolve to the EE overrides in the EE build (CE stubs throw)" — SAME import path both builds, webpack/nest path-mapping swaps the file. This is why the registry needs no conditional wiring.
single-query-cache.ts:8–13 — the CE stub carries a real constant (`nc_default_view`, "Namespaced with nc_ to avoid collision with real view IDs") plus a doc block explaining the full implementation lives EE-side; CE consumers like View.clearSingleQueryCache import through this path in BOTH builds.
single-query-cache.ts:15–30 — the HASH-design rationale preserved even in the stub's docs: every compiled single-query plan variant is a FIELD of one Redis hash per (model,view); invalidation is ONE atomic DEL; the previous SET-indexed design stranded variants whose independent expiry orphaned entries → Postgres 42703 "column does not exist" incident. The lesson lives on precisely BECAUSE the stub documents it.

## Flow / Invariant
Porter rule: an EE/CE split should (1) keep identical module paths in both builds, (2) make CE stubs THROW with a single canonical message rather than return junk, (3) keep pure constants/types in the CE file so cross-build consumers compile unchanged. Never silently no-op an unsupported dialect — the factory-returns-undefined pattern covers absence; stubs cover PRESENT-BUT-ENTERPRISE.

## Probe (direct test)
From repo root:
```
grep -c 'EE_ONLY' packages/nocodb/src/dbQueryClient/mssql.ts                                   # => 4 (decl + 3 throws)
grep -c 'EE_ONLY' packages/nocodb/src/dbQueryClient/oracle.ts                                  # => 5 (decl + 4 throws)
grep -rln 'enterprise (EE) build' packages/nocodb/src/dbQueryClient/mssql.ts packages/nocodb/src/dbQueryClient/oracle.ts packages/nocodb/src/dbQueryClient/aggregations/handlers/mssql.handler.ts packages/nocodb/src/dbQueryClient/aggregations/handlers/oracle.handler.ts | wc -l   # => 4 files
grep -n 'nc_default_view' packages/nocodb/src/dbQueryClient/cross-db-utils/single-query-cache.ts           # => 1 (:13)
grep -c '42703\|SET-indexed' packages/nocodb/src/dbQueryClient/cross-db-utils/single-query-cache.ts        # => 2 (:22,:23)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"MssqlAggregationHandler generate enterprise","limit":2,"detail":"compact"}'
```
→ `...mssql.handler.MssqlAggregationHandler.generate ... mssql.handler.ts 11-13`.

## Verdict
**Adopt.** This is the cleanest CE-stub doctrine in the codebase (extends ce-stub-parity-trace to query clients): same-path override, canonical throw message, constants stay put.
