<!-- capsule-v2 -->
# RecordQueryReadPlane — find/findOne/findStream with order-column fallback and CTE source

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does the read repository assemble record SELECTs (ordering, pagination, search, count, stream) and what fallbacks keep queries correct when optional columns are missing?

## Record query read plane
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordQueryRepository.ts` (whole file, 1-1056).
**Signature:** `find(context, table, spec?, options?) → Result<ITableRecordQueryResult, DomainError>`; `findOne(...)`; `findStream(...)` (async generator); `findByOffsetPage`/`findByCursorPage`.
**Data Shape:** options = `{ mode, projectionFieldIds?, orderBy?, pagination?, includeTotal?, search?, searchAccessPath?, recordReadQuerySource?, recordIdsOrder? }`. Order columns are `__row_*`; system columns `__auto_number`, `__created_time`, `__created_by`, `__last_modified_time`, `__last_modified_by`, `__version`, `__id`.

### Decisive source
```ts
// view row-order column may not exist → fall back to auto_number
if (column.startsWith('__row_')) {
  const columnExists = await this.getOrderColumnExists(dynamicDb, schemaName, tableNameOnly, column);
  if (columnExists) queryBuilder.orderBy(column, sort.direction);
  else queryBuilder.orderBy('__auto_number', 'asc');   // fallback
}
// explicit record-id order → array_position keeps the caller's ordering
if (explicitRecordIdsOrder?.length) {
  builtQuery = builtQuery.orderBy(
    sql`array_position(${orderedRecordIds}::text[], ${sql.ref(`${TABLE_ALIAS}.${RECORD_ID_COLUMN}`)})`);
}
// count runs in parallel with the rows query, sharing the same where+search
const [rows, countResult] = await Promise.all([rowsPromise, countPromise]);
```

**Flow:** create query builder (mode resolved: computed if any link/conditional field else stored) → apply projection, orderBy (with `__row_` existence fallback), pagination, spec → build where + search plan → optionally include order columns (`__row_%` from information_schema) → apply explicit record-id order via array_position → compile, run rows+count in parallel → `mapRowsToReadModels`. `findStream` drives offset/cursor pagination strategies in batches of 500, cursor requires `orderBy __auto_number asc` only.

**Invariant:** `__row_` order columns are optional — the query falls back to `__auto_number` when absent (5s TTL cache); count is skipped when `includeTotal===false`; cursor pagination is keyset on `__auto_number` and rejects any other ordering; `recordReadQuerySource` wraps the compiled SQL in a `WITH <cte> AS (...)` (CTE name validated `^[A-Z_]\w*$`).

**Probe:** `record/repository/PostgresTableRecordQueryRepository.pglite.spec.ts` — pins find/findOne/findStream ordering, pagination, and the `__row_` fallback.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PostgresTableRecordQueryRepository find findStream getOrderColumnExists array_position", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the order-column-existence fallback, parallel rows+count, and array_position record-id ordering. Adapt the `__row_`/`__auto_number` column names and 5s TTL. Omit the search access-path resolution (dedicated capsule). Probes pinned to the real pglite spec.
