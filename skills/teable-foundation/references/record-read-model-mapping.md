<!-- capsule-v2 -->
# RecordReadModelMapping — row→read-model with legacy avatar normalization

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does teable map a raw DB row to a `TableRecordReadModel` (system columns, order values, user-avatar URL normalization)?

## Row → read model mapping
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordQueryRepository.ts` (`mapRowsToReadModels` ~940-1020, `normalizeStoredUserAvatarUrls` ~1020-1070).
**Signature:** `mapRowsToReadModels(fieldColumns, rows, orderColumns): ReadonlyArray<TableRecordReadModel>`.
**Data Shape:** `TableRecordReadModel = { id, fields, version, autoNumber, createdTime, createdBy, lastModifiedTime, lastModifiedBy, orders? }`. `fieldColumns` come from `FieldOutputColumnVisitor` (fieldId + columnAlias + valueKind).

### Decisive source
```ts
// order columns __row_{viewId} → orders[viewId] = parsedOrder (finite only)
const viewId = colName.replace('__row_', '');
orders[viewId] = parsedOrder;
// user fields: rewrite legacy avatar URLs to the canonical builder
fields[column.fieldId.toString()] =
  column.valueKind === 'user' ? normalizeStoredUserAvatarUrls(value) : value;
```

**Flow:** per row: coerce `__id`→string, `__version`→number (or 0), extract `__auto_number`/`__created_time`/`__created_by`/`__last_modified_time`/`__last_modified_by`; if order columns requested, parse each `__row_{viewId}` into `orders[viewId]` (drop non-finite); map each field column into `fields[fieldId]`, running user-kind values through `normalizeStoredUserAvatarUrls`.

**Invariant:** `normalizeStoredUserAvatarUrls` rewrites only values containing the legacy prefix `/api/attachments/read/public/avatar/` — it recurses through JSON strings/arrays/objects and, when an object has an `id` and a legacy `avatarUrl`, replaces `avatarUrl` with `buildUserAvatarUrl(id)`; non-legacy values pass through untouched.

**Probe:** `record/repository/PostgresTableRecordQueryRepository.pglite.spec.ts` — pins the read-model shape and user-avatar normalization.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "mapRowsToReadModels normalizeStoredUserAvatarUrls buildUserAvatarUrl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the system-column extraction and the legacy-avatar rewrite (recursive, id-keyed). Adapt the `__row_`/`__` column names and the avatar URL prefix. Omit nothing portable. Probes pinned to the real pglite spec.
