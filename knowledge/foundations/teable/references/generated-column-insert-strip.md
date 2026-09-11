<!-- capsule-v2 -->
# Generated-column insert strip — how do you survive meta drift where a column is GENERATED ALWAYS on disk but the field metadata claims it is writable?

**Source:** teable AGPL `develop@06a4461e`. **Question:** PostgreSQL rejects INSERT of non-DEFAULT values into GENERATED ALWAYS columns — what best-effort safety net strips them before DML?

## information_schema probe + delete from every row map, swallow-your-own-errors
**Path/Symbol:** `PostgresTableRecordRepository.ts` — `collectUserAuditFieldColumnNames(table)` (:441–454), `stripPhysicallyGeneratedColumnsFromInsertValues(db, tableName, candidates, valuesList)` (:461–501), call sites in `insert` :1263–1270 and `insertMany` :1614–1621 (both commented T6146). Tests: insert.pglite.spec.ts suite exercises insert paths with legacy audit columns (suite at :286).
**Signature:** `(db, tableName, candidateColumnNames: string[], valuesList: Array<Record<string, unknown>>): Promise<void>` (mutates each values object).

### Decisive source
```sql
SELECT column_name FROM information_schema.columns
WHERE table_schema = ${schemaName ?? 'public'} AND table_name = ${plainTableName}
  AND column_name IN (${...presentColumns})
  AND is_generated IS DISTINCT FROM 'NEVER'      -- i.e. physically generated
```
```ts
for (const row of result.rows)
  for (const values of valuesList) delete values[row.column_name];
} catch { /* Best-effort safety net; insert will surface the original error if this fails. */ }
```

**Flow:** collect only createdBy/lastModifiedBy db column names (the fields known to have shipped as GENERATED ALWAYS) → intersect with keys actually present in the value maps → probe information_schema for those columns whose `is_generated` ≠ 'NEVER' → DELETE those keys from every row map → proceed with the INSERT.
**Invariant:** This exists ONLY because meta can drift from physical schema on legacy tables (`meta.persistedAsGeneratedColumn` lies) — the repository treats information_schema as ground truth for writability, not field metadata. The strip is deliberately NARROW (audit columns only) so a genuine bug cannot silently drop user data; and the whole helper swallows ITS OWN errors ("insert will surface the original error") — a catalog-probe failure must not become a different-looking failure. Porters who widen the candidate set to all fields turn this safety net into a data-loss vector; porters who let the catch rethrow convert a clean PG error into an opaque one.
**Probe:** deterministic: `grep -n "is_generated IS DISTINCT FROM 'NEVER'" PostgresTableRecordRepository.ts` (:486); behavior pinned by insert.pglite.spec.ts insert-path suites.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "stripPhysicallyGeneratedColumnsFromInsertValues is_generated GENERATED ALWAYS", limit: 5 });
```
## Verdict
Adopt the pattern for any system that mirrors logical schema into physical DDL: probe-and-strip against information_schema for known-drift-prone columns, narrow scope, fail-open to the real DB error.
