<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/generic.ts` :37–79 + `pg.ts` :16–22, `mysql.ts` :20–26, `sqlite.ts` :15–19.

# Question
How do you inject caller rows as a FROM-clause table and alias joined tables without breaking on Oracle?

## Path / Symbol
`GenericDBQueryClient.temporaryTableRaw / temporaryTable`, `tableAlias`, per-dialect `concat` / `simpleCast`.

## Signature
```ts
temporaryTableRaw(p: { data: Record<string,any>[]; fields: string[]; alias: string; knex: XKnex }): Knex.Raw
temporaryTable(param & { asKnexFrom?: boolean }): Knex.QueryInterface
tableAlias(knex: XKnex, table: string | Knex.Raw, alias: string): Knex.Raw
concat(fields: string[]): string;  simpleCast(field: string, asType: string): string
```

## Data Shape
temporaryTableRaw binds `(VALUES (?,?,...),(?,?,...)) AS alias (f1,f2,...)` — value placeholders `?` first, then alias + field names as identifier placeholders `??`; binding order in the flat array is **all row values first** (arrFlatMap over per-row field order), then alias, then fields (generic.ts:48–65).

## Decisive source
generic.ts:77–79 — base `tableAlias` = `` knex.raw(`?? as ??`, [table, alias]) ``. types.ts:66–71 documents the dialect fork this abstraction exists for: **Oracle rejects `AS` before a TABLE alias** (ORA-00907) while every other dialect accepts it — so the alias syntax is a method, not inline SQL. Consumer proof: group-by.ts:127–135 routes every derived-table wrap through `DBQueryClient.get(...).tableAlias(...)` with the comment "Oracle forbids AS on table aliases".
mysql.ts:23–26 — `simpleCast` maps SQL type TEXT→MySQL `CHAR` (`CAST(x as CHAR)`) before interpolating; pg uses native `::type`, sqlite plain CAST. These feed formula/lookup SQL where the cast TYPE keyword is dialect-specific even though CAST syntax is shared.
sqlite concat uses `||` join, mysql/pg CONCAT() (sqlite.ts:15–17 vs mysql.ts:20–22).

## Flow / Invariant
Porter trap: the VALUES-alias form `(VALUES ...) AS t(c1,c2)` is itself illegal on some engines (SQL Server requires derived-table column lists via `AS t(c1,c2)` exactly like this, Oracle needs `FROM (SELECT ... ) t`). NocoDB only ships the generic form because temporaryTable consumers run on pg/mysql/sqlite/mssql CE builds. The REAL portable invariant is: **table-position aliasing must go through a client method**, and **row injection must flatten values before identifiers in one bind array** — mixing the order corrupts every statement silently (placeholders are positional).

## Probe (direct test)
From repo root:
```
sed -n '48,65p' packages/nocodb/src/dbQueryClient/generic.ts | grep -c '??'     # => 2 lines carrying ?? placeholders (values-pair line + fields line; the raw template line has none)
grep -n 'as ??' packages/nocodb/src/dbQueryClient/generic.ts                    # => 1 hit (:78 tableAlias)
grep -c "CHAR" packages/nocodb/src/dbQueryClient/mysql.ts                       # => 1 (:25 TEXT→CHAR)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"temporaryTableRaw VALUES placeholder","limit":2,"detail":"compact"}'
```
→ `...generic.GenericDBQueryClient.temporaryTableRaw ... generic.ts 37-66`.

## Verdict
**Adopt.** Port the four micro-abstractions verbatim as an interface: they are the entire reason the same query code compiles across five dialects.
