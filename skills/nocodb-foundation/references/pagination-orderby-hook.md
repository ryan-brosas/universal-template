<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/generic.ts` :239–245 (`ensurePaginationOrderBy`) + `types.ts` :124–135 (interface doc) + CE/EE boundary comment `db/BaseModelSqlv2/group-by.ts` :734.

# Question
Where does dialect-specific pagination ordering plug in, and why is the base implementation a no-op?

## Path / Symbol
`GenericDBQueryClient.ensurePaginationOrderBy(qb, model)`; interface contract at types.ts:126–134.

## Signature
```ts
ensurePaginationOrderBy(qb: Knex.QueryBuilder, model: Model): void
```

## Data Shape
Void-mutating hook called on a list/sub-list query builder right before LIMIT/OFFSET application, AFTER all standard ORDER BY branches (user sorts, view sorts, Order column, PK, system CreatedTime) had their chance.

## Decisive source
generic.ts:239–245 — base body is a comment + no-op: "pg/mysql/sqlite — LIMIT/OFFSET runs without ORDER BY, so nothing to do. Mssql overrides this to satisfy T-SQL's OFFSET/FETCH rule." T-SQL rejects `OFFSET ... FETCH` without a preceding ORDER BY (Msg 102), so only MSSQL needs the last-resort deterministic sort.
types.ts:130–133 pins the portability contract in prose: "Implementations MUST be idempotent — they may be called even if an ORDER BY is already attached. The simplest correct implementation inspects qb and short-circuits."
group-by.ts:734 — a comment references "ensurePaginationOrderBy in the EE single-query client", showing the same hook name is re-used by the EE plan-cache client — the method is part of the cross-build client surface, not an internal helper.
The interface doc also states call timing (:125–128): "Last-resort ORDER BY injection... AFTER the usual ORDER BY branches... have had a chance" — i.e. it exists for the corner where NO branch added ordering yet pagination is about to run.

## Flow / Invariant
Design rule worth porting whole-cloth: **pagination-legality is a dialect concern, so it lives on the dialect object as an idempotent final hook** rather than polluting shared orchestration with `if (isMssql)` branches. Any engine that requires ORDER BY with OFFSET (old SQL Server, some ANSI modes) overrides; others inherit the no-op.

## Probe (direct test)
From repo root:
```
sed -n '239,245p' packages/nocodb/src/dbQueryClient/generic.ts | grep -c 'no-op\|nothing'   # => 2 comment markers
grep -rn 'ensurePaginationOrderBy' packages/nocodb/src/db --include='*.ts' | wc -l          # => 1 (group-by.ts comment :734)
grep -n 'MUST be idempotent' packages/nocodb/src/dbQueryClient/types.ts                     # => 1 (:132)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"ensurePaginationOrderBy OFFSET FETCH","limit":2,"detail":"compact"}'
```
→ `...generic.GenericDBQueryClient.ensurePaginationOrderBy ... generic.ts 243-245`.

## Verdict
**Adopt.** Port as pattern: idempotent last-resort pagination hook on the dialect client, no-op base, override per engine requirement.
