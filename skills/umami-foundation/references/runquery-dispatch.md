<!-- capsule-v2 -->
# runQuery dual-backend dispatch — how does one analytics codebase serve Postgres AND ClickHouse without an ORM abstraction?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How is backend selection routed per-query with two hand-written SQL implementations?

## runquery-dispatch
**Path/Symbol:** `src/lib/db.ts:runQuery/getDatabaseType/isRelationalOnly :26-44`; exemplar callers `src/queries/sql/getActiveVisitors.ts:8-13`, `src/queries/sql/getWebsiteStats.ts:24-30`.
**Signature:** `runQuery({ [PRISMA]: fn, [CLICKHOUSE]: fn })` — string-constant keyed map; CLICKHOUSE wins whenever `CLICKHOUSE_URL` is set, else PRISMA (Postgres only).
**Data Shape:** every query module exports ONE function + two private `relationalQuery`/`clickhouseQuery` bodies returning the SAME row shape (`as "camelCase"` aliases in both SQL dialects).

### Decisive source
```ts
export async function runQuery(queries: any) {
  if (process.env.CLICKHOUSE_URL) {
    if (queries[KAFKA]) return queries[KAFKA]();   // optional kafka leg for writes
    return queries[CLICKHOUSE]();
  }
  const db = getDatabaseType();                     // from DATABASE_URL scheme
  if (db === POSTGRESQL) return queries[PRISMA]();
}
```

**Flow:** caller → `runQuery` → dialect-specific SQL builder (each side has its own param syntax: `{name:Type}` for CH vs `{{name::uuid}}` for prisma raw) → same JSON column aliases out.
**Invariant:** the contract is RESULT-SHAPE equality, not SQL equality: any new filter/column must be implemented in BOTH bodies or the app silently diverges by deployment mode. `FUNCTION_NAME` string tags each raw query for LOG_QUERY tracing — keep it.
**Probe:** `grep -rc "runQuery({" src/queries/sql --include="*.ts" | grep -v ":0" | wc -l` → ≥25 files dispatch through it.
**Probe:** `grep -n "queries\[KAFKA\]" src/lib/db.ts` → :31.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "runQuery relationalQuery clickhouseQuery dispatch", limit: 10 });
```

## Verdict
Adopt constant-keyed function-map dispatch when you must support two storage engines with dialect-native SQL and no leaky abstraction; adapt the selection env vars; omit the Kafka write leg if you have no queue tier.
