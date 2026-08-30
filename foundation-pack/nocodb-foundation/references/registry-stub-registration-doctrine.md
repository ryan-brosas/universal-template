<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/index.ts` :15–23 + `handlers/mssql.handler.ts` :10–14 + `handlers/oracle.handler.ts` (14L) — the registry's stub entries.

# Question
Why does the CE aggregation registry REGISTER dialects it cannot serve instead of omitting them?

## Path / Symbol
`AGGREGATION_HANDLER_REGISTRY[ClientType.MSSQL] = MssqlAggregationHandler` (CE throwing stub); same for ORACLE.

## Data Shape
Registry type is `Partial<Record<ClientType, new () => AggregationHandlerInterface>>` — Partial permits omission, yet five of six ClientTypes are present with two being throw-stubs.

## Decisive source
aggregations/index.ts:6 — "mssql / oracle resolve to the EE overrides in the EE build (CE stubs throw)." Registering the CE stub keeps `getAggregationHandler(MSSQL)` returning a HANDLER whose generate() throws the canonical EE_ONLY message (:11–13) rather than the REGISTRY throwing 'No aggregation handler registered for client MSSQL' (:33–36). Two distinct error texts ⇒ two distinct diagnoses: registered-but-EE = licensing/deployment answer; unregistered = genuine code gap (new ClientType nobody wired).
The contrast case proves intent: DBQueryClient.get() (index.ts) DOES return undefined for unsupported types at the CLIENT layer, while the HANDLER layer prefers loud typed errors. Absence at the client factory, presence-with-throw at the strategy layer.

## Flow / Invariant
Design rule: register every dialect you can NAME so error messages classify themselves; omit only what you cannot name. Porters who trim "unused" stub entries from the registry break that diagnosis channel and turn every EE-dialect question into 'No aggregation handler registered' noise.

## Probe (direct test)
From repo root:
```
grep -n 'ClientType\.' packages/nocodb/src/dbQueryClient/aggregations/index.ts                       # => 5 keys
sed -n '32,37p' packages/nocodb/src/dbQueryClient/aggregations/index.ts | grep -c 'No aggregation handler registered'   # => 1
grep -l 'EE build' packages/nocodb/src/dbQueryClient/aggregations/handlers/*.ts                      # => 2 files (mssql+oracle stubs)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"AGGREGATION_HANDLER_REGISTRY","limit":2,"detail":"compact"}'
```
→ resolves index.ts 15-23 line-exact.

## Verdict
**Adopt.** Registry-with-typed-stubs beats registry-with-holes for operability; pair with query-client-ee-stub-doctrine.
