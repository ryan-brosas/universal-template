<!-- capsule-v2 -->
# db-error extractor dispatch — how does an arbitrary driver error become a typed, client-attributed extraction without being told which database it came from?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When a raw Knex/driver error bubbles up, who decides which dialect's extractor parses it — and what happens when detection fails?

## Client-type fingerprinting + registry dispatch

**Path/Symbol:** `packages/nocodb/src/helpers/db-error/extractor.ts:DBErrorExtractor.detectClientType` (:57–99), `extractDbError` (:101–130), singleton `DBErrorExtractor._` (:16–19), per-client extractor Map (:21–52).
**Signature:** `extractDbError(error: any, option?: { clientType?: ClientType; ignoreDefault?: boolean }): Promise<DBErrorExtractResult | undefined>` (sync in practice; returns `{message, error, details?, code?, httpStatus}` or `undefined`).
**Data Shape:** Registry is a `Map<ClientType, IClientDbErrorExtractor>` seeded with Pg/Sqlite/Mysql/Mssql/Oracle extractors sharing ONE NestJS `Logger('MissingDBError')`; `DefaultDBErrorExtractor` sits OUTSIDE the map as the last-resort fallback. `DBErrorExtractResult` = `{ message: string; error: string; details?: any; code?: string; httpStatus: number }`.

### Decisive source
```ts
// :57-99 — code-shape fingerprinting, ordered most-specific first
if (code.startsWith('ER_')) return ClientType.MYSQL;
if (code.startsWith('ORA-') || code.startsWith('NJS-')) return ClientType.ORACLE;
if (/^[0-9A-Z]{5}$/.test(code)) return ClientType.PG;
if (code.startsWith('SQLITE_')) return ClientType.SQLITE;
// tedious driver-level list incl. 'EINVALIDSTATE'
...
if (typeof error?.number === 'number') return ClientType.MSSQL;   // server-side tedious
if (typeof error?.errorNum === 'number') return ClientType.ORACLE; // node-oracledb server errors
```

**Flow:** explicit `option.clientType` wins → else fingerprint from `error.code` shape (MySQL `ER_*`, Oracle `ORA-*`/`NJS-*`, PG five-char SQLSTATE `[0-9A-Z]{5}`, SQLite `SQLITE_*`, MSSQL tedious codes ELOGIN/ETIMEOUT/ESOCKET/EREQUEST/EABORT/ECANCEL/EINVALIDSTATE) → else property probes (`number` ⇒ MSSQL, `errorNum` ⇒ Oracle) → if a client matched, run ONLY its extractor → if NO client matched, trial-and-first-success across ALL FIVE extractors (`forEach` keeps first non-undefined result) → still nothing and `!option.ignoreDefault` ⇒ `defaultExtractor.extract(error)`.
**Invariant:** (1) The PG regex accepts ANY 5-char alphanumeric-uppercase code — MySQL `ER_*`/Oracle prefixes must be checked BEFORE it or they'd never match (order is load-bearing). (2) The unknown-client fan-out relies on every extractor returning `undefined` for foreign shapes (`if (!error.code) return;` guards); a porter whose extractor throws instead of returning undefined breaks the trial ladder. (3) `ignoreDefault:true` is how callers (formula dry-run, global filter) opt out of the generic 500-shaped default and keep raw text for triage. (4) XX000-class internal errors may return undefined ON PURPOSE (see pg capsule) — `undefined` is a valid, meaningful result, not a failure.

### Porting traps (each verified against source)
- tedious sets its driver codes on EVERY error including wrappers around server errors — the comment pins that MSSQL detection therefore also catches server errors "which additionally carry `number`" (:75–77).
- node-oracledb connection failures raise BEFORE any SQL runs as `NJS-xxx` — classified ORACLE at the same branch as `ORA-*` (:64–67).
- In-file anchors: `grep -n "code.startsWith('ER_')" src/helpers/db-error/extractor.ts` → 1 hit; `grep -c "'EINVALIDSTATE'" src/helpers/db-error/extractor.ts` → 1; `grep -c "typeof error?.number === 'number'" src/helpers/db-error/extractor.ts` → 1; `grep -c 'NJS-' src/helpers/db-error/extractor.ts` → 2 (comment + code).

**Probe:** No upstream unit spec imports this plane (109 spec files grepped, jest bin absent — runner-blocked caveat). Deterministic probe from repo root:
`cd packages/nocodb && grep -n "code.startsWith('ER_')" src/helpers/db-error/extractor.ts` → `62:` and `sed -n '78,90p' src/helpers/db-error/extractor.ts | grep -c EINVALIDSTATE` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "DBErrorExtractor extractDbError detectClientType", limit: 10 });
```
Resolves `detectClientType` :57-99 rank-1, `extractDbError` :101-130 rank-2, consumer `helpers/catchError.extractDBError` :26-41 rank-3 (`has_more: true`).

## Verdict
Adopt the fingerprint-order (dialect prefixes before the 5-char SQLSTATE catch-all), the trial-all-on-unknown ladder, and the outside-map default extractor; adapt ClientType enum to host; omit NestJS Logger wiring. Coverage caveat: no direct tests at pin; probes are source-greps honestly labeled.
