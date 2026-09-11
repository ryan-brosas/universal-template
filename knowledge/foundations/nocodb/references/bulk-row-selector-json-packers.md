<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/pg.ts` :24–38, `mysql.ts` :28–48, `sqlite.ts` :22–35 — the three `bulkAggregateRowSelector` implementations side-by-side.

# Question
Why do the three JSON row packers differ in quoting and LIMIT placement, and what breaks if you normalize them?

## Path / Symbol
`{PG|MySql|Sqlite}DBQueryClient.bulkAggregateRowSelector(baseModel, tQb, expressions, alias)`.

## Signature
```ts
// pg:      tQb.select(knex.raw(`JSON_BUILD_OBJECT('id', expr, ...)`));            return knex.raw('(??) as ??', [tQb, alias])
// mysql:   tQb.select(knex.raw(`JSON_UNQUOTE(JSON_OBJECT('id', expr, ...))`)).limit(1);  same wrap
// sqlite:  tQb.select(knex.raw(`json_object('id', expr, ...)`));                  same wrap
```

## Data Shape
expressions: Record<colId, aggSqlString>; keys interpolated as SINGLE-QUOTED literals (`` '${k}' ``) with the SQL expression text spliced raw after each key.

## Decisive source
mysql.ts:39–46 — TWO documented deviations: (1) JSON_UNQUOTE because MySQL's JSON_OBJECT returns a JSON type whose string form double-escapes; execAndParse's `startsWith('{')` parse contract needs TEXT. (2) `.limit(1)` "median/attachment-size are non-aggregate scalar subqueries... without it the wrapped SELECT returns one row per filtered row → 'subquery returns more than 1 row'". pg/sqlite need neither: percentile_cont/json_object paths aggregate or scalarize naturally.
pg.ts:32–34 vs mysql.ts:35–38 — identical `'${k}', ${expressions[k]}` splicing; key injection is safe ONLY because keys are NocoDB column ids (uuid-ish), never user text.
All three return `(tQb) as alias` derived-table selectors so the outer bulk query unions one column per bucket.

## Flow / Invariant
Porter rules: (1) keys must be server-safe ids — never splice user-controlled field names into this template; (2) MySQL's limit(1) is load-bearing for ANY non-aggregate subquery expression; (3) keep JSON-as-TEXT on MySQL or the bulk parse stage silently no-ops (string starts with '"' not '{').

## Probe (direct test)
From repo root:
```
grep -n 'JSON_BUILD_OBJECT' packages/nocodb/src/dbQueryClient/pg.ts          # => 1 (:32)
grep -n 'JSON_UNQUOTE' packages/nocodb/src/dbQueryClient/mysql.ts            # => 1 (:35)
grep -c '\.limit(1)' packages/nocodb/src/dbQueryClient/mysql.ts              # => 1 (:46 call; :43 comment mentions `limit(1)` in backticks)
grep -c 'as ??' packages/nocodb/src/dbQueryClient/pg.ts packages/nocodb/src/dbQueryClient/mysql.ts packages/nocodb/src/dbQueryClient/sqlite.ts   # => 1 per file
grep -c "'\${k}'" packages/nocodb/src/dbQueryClient/pg.ts                    # => 1 (:33)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"bulkAggregateRowSelector","limit":4,"detail":"compact"}'
```
→ resolves oracle/mysql/pg (+sqlite via has_more) methods line-exact.

## Verdict
**Adapt.** Port all three verbatim including their asymmetries — normalizing them reintroduces the MySQL >1-row regression.
