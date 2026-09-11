<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/index.ts` (whole file, 69L).

# Question
How does NocoDB map a runtime database connection to the right dialect client class — and what happens for a dialect with no CE implementation?

## Path / Symbol
`DBQueryClient.get(clientType, dbVersion?)`, `DBQueryClient.fromKnex(knex, dbVersion?)`

## Signature
```ts
static get(clientType: ClientType | DriverClient, dbVersion?: string): DBQueryClientType
static fromKnex(knex: Knex, dbVersion?: string): DBQueryClientType   // index.ts:47
```

## Data Shape
`get()` switches over the SDK `ClientType` enum plus the nc-config `DriverClient.MYSQL_LEGACY` value; `fromKnex()` normalizes three possible knex config shapes before matching string keys `'pg' | 'mysql' | 'mysql2' | 'sqlite3' | 'mssql' | 'oracledb'`.

## Decisive source
index.ts:17–44 — the switch has **no default arm**: an unknown/unsupported `ClientType` leaves `client` undefined and `if (client)` skips the assignment, so `get()` returns **`undefined`**, not an error. Callers (`data-table.service.ts:140`, `public-datas.service.ts:337`) immediately dereference `.aggregate(...)`, so an unsupported source type surfaces as a TypeError at the service boundary — fail-fast by omission, never a constructed stub client.
index.ts:22–27 — MYSQL falls through into `MYSQL_LEGACY` sharing one `MySqlDBQueryClient` (the eslint-disable comment marks it deliberate).
index.ts:41–43 — `dbVersion` is stamped AFTER construction as a plain property; handlers read it off the client instance later.
index.ts:48–52 — `fromKnex` reads `knex.client?.config?.client` which may be a string OR an adapter class; it probes `cfgClient?.prototype?.dialect || cfgClient?.prototype?.driverName`. Unknown knex client ⇒ explicit `throw new Error('DBQueryClient: unsupported knex client ...')` (:66).

## Flow / Invariant
Porters get this wrong twice:
1. **`get()` is total-by-returning-undefined** — do NOT add a default throw inside the switch; upstream deliberately lets undefined flow so EE-only dialects degrade at the caller, not in the factory. But `fromKnex()` DOES throw explicitly. The two factories have opposite failure modes by design: `get` = silent undefined (enum-driven, callers guard), `fromKnex` = loud error (string-driven, transaction paths cannot guard).
2. The instance is created fresh on EVERY call — no caching, no pooling of client objects; `dbVersion` must be re-stamped per call or it silently stays `undefined`.

## Probe (direct test)
No upstream spec imports `DBQueryClient` (109 spec files grepped — recorded gap). Source-grounded probe from repo root:
```
sed -n '16,44p' packages/nocodb/src/dbQueryClient/index.ts | grep -c 'case'   # => 6 (PG, MYSQL, MYSQL_LEGACY, SQLITE, MSSQL, ORACLE)
grep -c "default:" packages/nocodb/src/dbQueryClient/index.ts                # => 0 in get(); fromKnex's default throw is at :65-66 -> total file count 1
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"DBQueryClient.fromKnex knex client","limit":2,"detail":"compact"}'
```
→ `...dbQueryClient.DBQueryClient.fromKnex Method packages/nocodb/src/dbQueryClient/index.ts 47-68`.

## Verdict
**Adopt.** Any multi-dialect port needs both factories exactly as-is: enum-side silent-undefined, knex-string-side throwing, shared fallthrough for legacy MySQL, post-construction dbVersion stamping.
