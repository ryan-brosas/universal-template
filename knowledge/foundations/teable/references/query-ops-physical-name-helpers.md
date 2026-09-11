<!-- capsule-v2 -->
# Query-ops physical-name helpers — how does teable safely resolve a logical table to its schema-qualified physical name and quote identifiers?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Every advisor/executor needs the physical `schema.table` for a logical table and must quote identifiers/values safely against SQL injection. What's the shared helper contract?

## getTablePhysicalName + quoteIdentifier + makePhysicalTableSql + toInfrastructureError
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/helpers.ts` — `getTablePhysicalName` (10–21), `quoteIdentifier` (23), `makePhysicalTableSql` (25–26), `toInfrastructureError` (4–8); `executor.ts`/`searchVector.ts` `splitPhysicalName` (executor.ts 173–182, searchVector.ts 2869–2881).
**Signature:** `getTablePhysicalName(table): Result<{schema, tableName}, DomainError>`; `quoteIdentifier(value): string`; `makePhysicalTableSql(schema, tableName): string`.
**Data Shape:** physical name = `{schema, tableName}` where schema is the table's `baseId` unless `db_table_name` is `schema.table` (then split on the first dot).

### Decisive source
```ts
export const getTablePhysicalName = (table) => {
  const dbTableName = table.dbTableName();
  if (dbTableName.isErr()) return err(dbTableName.error);
  const split = dbTableName.value.split({ defaultSchema: table.baseId().toString() }); // Result
  if (split.isErr()) return err(split.error);
  if (!split.value.schema) return err(domainError.validation({ message: 'Table physical schema is missing' }));
  return ok({ schema: split.value.schema, tableName: split.value.tableName });
};
export const quoteIdentifier = (value) => `"${value.replace(/"/g, '""')}"`;   // double the quotes
export const makePhysicalTableSql = (schema, tableName) => `${quoteIdentifier(schema)}.${quoteIdentifier(tableName)}`;
// splitPhysicalName (executor) — first-dot split, default schema when no dot:
const dotIndex = dbTableName.indexOf('.');
if (dotIndex === -1) return { schema: defaultSchema, tableName: dbTableName };
return { schema: dbTableName.slice(0, dotIndex), tableName: dbTableName.slice(dotIndex + 1) };
```

**Flow:** `getTablePhysicalName` resolves the logical table's physical name through the core `dbTableName()` Result, splitting against the base-id default schema and failing with a validation error if the schema is missing; `quoteIdentifier` doubles embedded quotes (Postgres rule) so any identifier is safe; `makePhysicalTableSql` composes the quoted `schema.table`; `splitPhysicalName` is the raw-string twin used when reading `db_table_name` directly from `table_meta`.
**Invariant:** every identifier interpolated into SQL goes through `quoteIdentifier` (never raw); physical names are always schema-qualified; the split treats a bare `db_table_name` as `defaultSchema.table` and a dotted one as `schema.table` (first-dot split).
**Probe:** no dedicated unit spec; exercised by every advisor/executor DB path that resolves a table.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getTablePhysicalName quoteIdentifier makePhysicalTableSql splitPhysicalName", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Result-returning physical-name resolver, quote-doubling identifier escaper, and schema-qualified table composer; adapt the default-schema source to host; omit teable's core `Table.dbTableName()` Result coupling if the host resolves names differently. Coverage: fully indexed.
