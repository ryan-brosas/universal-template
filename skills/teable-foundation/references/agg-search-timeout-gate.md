<!-- capsule-v2 -->
# DB-level search timeout — SET LOCAL statement_timeout inside the data transaction

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does a short/CJK search term that defeats the pg_trgm index get killed WITHOUT starving the connection pool?

## Server-side cancel + three-shape error duck-typing
**Path/Symbol:** `apps/nestjs-backend/src/features/aggregation/aggregation.service.ts:getRecordIndexBySearchOrder` — SET LOCAL :1035 with design comment :1031–1034, headroom comment :1100–1101, catch→timeout mapping :1103–1116; detector `isSearchTimeoutError` (:1129–1145); threshold `configs/threshold.config.ts:25` (`SEARCH_TIMEOUT ?? 15_000`).
**Signature:** `withDataPrismaTransaction(tableId, async (prisma) => { await prisma.$executeRawUnsafe(\`SET LOCAL statement_timeout = ${searchTimeout}\`); ... })`.
**Data Shape:** timeout in ms; Postgres cancels with SQLSTATE 57014.

### Decisive source
```ts
// Bound the search at the DB level: a short / CJK term can defeat the pg_trgm index and
// degrade to a full-table scan. SET LOCAL statement_timeout makes Postgres cancel the
// statement and release the pooled connection...
await prisma.$executeRawUnsafe(`SET LOCAL statement_timeout = ${searchTimeout}`);
```
```ts
return (
  err.code === 'P2028' ||
  err.code === 'request_timeout' ||
  pgErrorCode === '57014' ||
  /canceling statement due to statement timeout|Transaction already closed/i.test(message)
);
```

**Flow:** Inside the interactive transaction: SET LOCAL scopes the timeout to THIS transaction → run the search SQL → on cancel, Postgres error 57014 propagates through Prisma's separate generated runtime where cross-package `instanceof` is unreliable, so detection duck-types THREE shapes: P2028 (interactive-tx timeout), 'request_timeout' (proxy-converted), 57014/message-regex (real DB cancel) → rethrown as REQUEST_TIMEOUT http error.
**Invariant:** The comment chain encodes two porters-get-wrong facts: (1) the JS-side tx timer must be LARGER than the DB timeout ("give the JS-side tx timer headroom so Postgres cancels the statement first") — otherwise the transaction aborts before the statement does and the pooled connection leaks; (2) SET LOCAL not SET — a session-level timeout would leak to subsequent borrowers of the pooled connection. Detection must be shape-based because the data-db Prisma client is a SEPARATE generated runtime from the meta client (BYODB): instanceof across packages silently fails.
**Probe:** `grep -cF 'statement_timeout' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 4; `grep -cF '57014' apps/nestjs-backend/src/features/aggregation/aggregation.service.ts` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "isSearchTimeoutError statement_timeout searchTimeout", limit: 10 });
```

## Verdict
Adopt transaction-scoped statement timeouts for user-triggered searches; adapt the error duck-typing to your driver's error shapes; keep DB-timeout < client-tx-timeout ordering.
