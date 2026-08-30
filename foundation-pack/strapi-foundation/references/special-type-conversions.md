<!-- capsule-v2 -->
# Special type-conversion pre-pass — how do you apply lossy dialect-specific column changes without double processing?

**Source:** Strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** Some column type changes need raw dialect SQL (e.g. Postgres `ALTER ... USING`), not a knex `.alter()` — where do they run, and how do you stop the generic ladder from repeating them?

## Dialect conversion SQL runs before the standard alter ladder and removes itself from the diff
**Path/Symbol:** `packages/core/database/src/schema/builder.ts` : `handleSpecialTypeConversions` (513–580), called from `updateSchema` before each `alterTable`.
**Signature:** `async handleSpecialTypeConversions(trx: Knex.Transaction, table: TableDiff['diff'], preloadedColumnTypes: Record<string, string|null> = {})`.
**Data Shape:** consults `db.dialect.getColumnTypeConversionSQL(currentType, targetType)` → `{ sql, warning? } | null`; mutates `table.columns.updated` in place.

### Decisive source
```ts
if (db.config.connection.client !== 'postgres') {
  return;                                   // Only PostgreSQL needs special handling for now
}
for (const updatedColumn of table.columns.updated) {
  const currentType = preloadedColumnTypes[columnName] ?? (await getCurrentColumnType(table.name, columnName));
  if (currentType) {
    const conversionSQL = db.dialect.getColumnTypeConversionSQL(currentType, column.type);
    if (conversionSQL) conversionsToApply.push({ column: updatedColumn, sql: conversionSQL.sql,
      params: [table.name, columnName, columnName], currentType, targetType, warning: conversionSQL.warning });
  }
}
// ...
try {
  await trx.raw(sql, params);               // inside the SAME sync transaction
} catch (conversionError) {
  db.logger.error(`Failed to convert column ${column.name}: ${...}`);
  throw conversionError;
}
await applyColumnProperties(trx, table.name, column.name, column.object);
// Remove from standard updates to prevent double processing
table.columns.updated = table.columns.updated.filter((col) => col.name !== column.name);
```

**Flow:** per updated column on postgres → resolve live current type (from the pre-fetched map) → ask the dialect for bespoke conversion SQL → execute it raw inside the sync transaction → apply remaining column properties → delete the entry from the diff so `alterTable` never touches that column again.
**Invariant:** exactly one mechanism owns each column mutation. If the special path succeeds but forgets to remove the diff entry, the generic ladder re-alters (and may re-run a lossy cast); if it fails it rethrows so the whole transaction rolls back — no half-converted columns.
**Probe:** no dedicated unit test pins this helper (dialect-bound); the observable contract lives in the source invariant comment plus the postgres-only early return. Record as a direct-test caveat when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "schema sync builder synchronize database schema status", limit: 25, fields: ["lines", "signature"] });
// returned builder.handleSpecialTypeConversions @ builder.ts 513-580 alongside updateSchema/alterTable
```

## Verdict
Adopt the "dialect hook + self-removing diff entry" pattern for any lossy type migration and the warn-before-lossy-change logging. Adapt the trigger condition (postgres-only today) by asking your dialect registry instead of hardcoding clients. Omit Strapi's specific `getColumnTypeConversionSQL` implementations.
