<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/generic.ts` :26–36 (`clientType` getter + `validateClientType`) + `mysql.ts` :14–18 override + `dbQueryClient/types.ts` :46–51.

# Question
Why does every dialect client carry its own type identity AND a validator that other code calls with the SOURCE's client string?

## Path / Symbol
`GenericDBQueryClient.clientType` (base getter returns `ClientType.PG`), `validateClientType(client: string)`; MySqlDBQueryClient.validateClientType override.

## Signature
```ts
get clientType(): ClientType            // overridden per subclass
validateClientType(client: string): void  // throws 'Source is not <type>' on mismatch
```

## Data Shape
Base implementation compares the incoming string against `this.clientType` enum value directly (:32–36).

## Decisive source
generic.ts:29–31 — the BASE getter hard-returns PG; it exists only so TypeScript's interface is satisfiable and as a last-ditch default — every concrete class overrides. A porter who instantiates GenericDBQueryClient directly gets pg semantics silently.
generic.ts:32–36 — base validator: `if (client !== this.clientType) throw new Error('Source is not ' + this.clientType)`.
mysql.ts:14–18 — MySQL MUST override because knex reports `'mysql'` OR `'mysql2'` for the same server: `if (!['mysql','mysql2'].includes(client)) throw`. The error MESSAGE still names the enum ('Source is not MYSQL') — identity stays canonical even when admission is looser.
Consumers: sql-client/NC connection plumbing calls validateClientType(source.type) when a source's driver must match the model being served — mismatch = misconfigured source, fail fast before any SQL compiles.

## Flow / Invariant
Two-port rule: (1) `clientType` is IDENTITY (used for registry dispatch + handler lookup); (2) `validateClientType` is ADMISSION (accepts all wire aliases of that engine). Collapsing them — e.g. validating by comparing to knex strings while dispatching on enums — breaks either dispatch or aliasing. The mysql2 alias list is the only CE divergence; EE clients re-widen their own.

## Probe (direct test)
From repo root:
```
sed -n '29,36p' packages/nocodb/src/dbQueryClient/generic.ts | grep -c 'ClientType.PG\|!== this.clientType'   # => 2 hits
grep -c "'mysql2'" packages/nocodb/src/dbQueryClient/mysql.ts                                  # => 1 (:15)
grep -rc 'Source is not ' packages/nocodb/src/dbQueryClient/generic.ts packages/nocodb/src/dbQueryClient/mysql.ts | awk -F: '{s+=$NF} END {print s}'   # => 2 (1 per file)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"validateClientType Source is not","limit":3,"detail":"compact"}'
```
→ resolves both validators line-exact.

## Verdict
**Adopt.** Keep identity/admission split and the per-engine alias widening exactly.
