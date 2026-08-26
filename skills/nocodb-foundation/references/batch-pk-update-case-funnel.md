<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/generic.ts` :93–164 (`batchUpdate`) plus the Oracle override `oracle.ts` :27–34.

# Question
How does NocoDB update hundreds of rows by primary key in ONE round trip — and why does Oracle not just override the SQL text?

## Path / Symbol
`GenericDBQueryClient.batchUpdate({ knex, tnPath, rows, pkColumnName })`

## Signature
```ts
batchUpdate(payload: { knex: XKnex; tnPath: string | Knex.Raw;
  rows: Record<string, any>[]; pkColumnName: string; }): Knex.QueryBuilder | Knex.Raw | null
```

## Data Shape
Emits one UPDATE of the form:
```sql
UPDATE table SET
  col1 = CASE pk WHEN 1 THEN 'v1' WHEN 2 THEN 'v2' ELSE col1 END,
  col2 = CASE pk WHEN 1 THEN 'v3' ELSE col2 END
WHERE pk IN (1, 2)
```
Per-column: only rows that HAVE that column contribute WHEN arms; columns absent from every row are skipped entirely.

## Decisive source
generic.ts:104–128 — three early `return null`s that a porter WILL miss: empty rows; no row carries the pk (filter `!ncIsUndefined(row[pkColumnName])`); union of non-pk column names is empty. Callers treat null as "nothing to do", NOT an error.
generic.ts:136–139 — per-column filteredRows excludes rows where THAT column is undefined — otherwise knex binds literal `undefined` and **MSSQL's binding-validation pass rejects the whole statement** ("Undefined binding(s) detected for keys [1] when compiling RAW query: CASE [id] WHEN ? THEN ?" — quoted verbatim in the source comment).
generic.ts:149–154 — value normalization at bind time: only null/object/array/boolean pass through as-is; everything else is template-stringified (`${row[column]}`) so numbers bind as strings uniformly across drivers.
generic.ts:163 — `knex(tnPath).update(updateObj).whereIn(pkColumnName, pks)` — pks is deduped via `[...new Set(...)]` (:115) so duplicate pk rows collapse into the IN list.
oracle.ts:27–34 — Oracle throws EE_ONLY instead of overriding the CASE shape. The doc comment on generic.ts:89–91 records WHY Oracle cannot reuse it: its CASE types from the FIRST THEN clause and rejects the differently-typed `ELSE col1` reference (ORA-00932) — i.e. the fallback-per-row loop in BaseModelSqlv2 (:4500–4516, gated to pg/mysql/sqlite/mssql by `primaryKeys.length === 1 && dialect`) silently handles Oracle instead.

## Flow / Invariant
The invariant: **every bound value must be defined and every targeted row must have the pk**, else the single-statement batch either fails validation (MSSQL) or updates nothing for that row (CASE never matches ⇒ ELSE keeps old value — which is exactly why missing-pk rows are DROPPED up front rather than included).
Caller contract (BaseModelSqlv2.ts:4499–4503): batchUpdate is used ONLY inside an explicit transaction with single-pk models; the surrounding code falls back to per-row UPDATEs otherwise.

## Probe (direct test)
No upstream spec imports batchUpdate (recorded gap). From repo root:
```
sed -n '104,128p' packages/nocodb/src/dbQueryClient/generic.ts | grep -c 'return null'          # => 4 (three guards + empty-updateObj guard at :127)
grep -c 'Undefined binding' packages/nocodb/src/dbQueryClient/generic.ts                        # => 1 (the MSSQL comment)
grep -c 'EE_ONLY' packages/nocodb/src/dbQueryClient/oracle.ts                                   # => 5 (decl + 4 throws)
grep -c 'ORA-00932' packages/nocodb/src/dbQueryClient/generic.ts                                # => 1 (the CASE-typing comment)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"batchUpdate CASE WHEN primary key","limit":2,"detail":"compact"}'
```
→ `...generic.GenericDBQueryClient.batchUpdate ... generic.ts 93-164`.

## Verdict
**Adapt.** The CASE-batch shape ports directly to any SQL dialect with typed CASE; porters must keep all three null-returns, the undefined-row filter per column, the MSSQL binding rationale, and the Oracle exclusion (fall back to per-row loop, do NOT port the CASE form).
