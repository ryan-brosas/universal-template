<!-- capsule-v2 -->
# Unique-index & empty-string repair twins — how are declared constraints re-materialized and '' cells normalized?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does teable restore missing UNIQUE indexes without guessing index names, and why do empty strings get NULLed instead of kept?

## UniqueIndexService + checkEmptyString/fixEmptyString
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/unique-index.service.ts:checkUniqueIndex` (:20–61), `:fixUniqueIndex` (:62–110); `apps/nestjs-backend/src/features/integrity/link-integrity.service.ts:checkEmptyString` (:436–481), `:fixEmptyString` (:1235–1268).
**Signature:** `fixUniqueIndex(tableId?, fieldId?)`; `checkEmptyString(tableId): Promise<IIntegrityIssue[]>`.
**Data Shape:** Index discovery via `fieldService.findUniqueIndexesForField(tableId, dbTableName, dbFieldName)`; empty-string scan limited to `cellValueType=String && dbFieldType=Text && isComputed=null`.

### Decisive source
```ts
if (fieldId.startsWith('__')) {
  sql = this.knex.schema.alterTable(table.dbTableName, (table) => {
    table.unique([fieldId]);                       // system column → default name
  }).toQuery();
} else if (fieldId.startsWith(IdPrefix.Field)) {
  const indexName = this.fieldService.getFieldUniqueKeyName(
    table.dbTableName, field.dbFieldName, fieldId);
  sql = this.knex.schema.alterTable(table.dbTableName, (table) => {
    table.unique([field.dbFieldName], { indexName });   // field column → deterministic name
  }).toQuery();
}
```
```ts
const countSql = await this.knex(dbTableName)
  .count('*').whereRaw(`?? = ''`, [dbFieldName]).toQuery();
...
const sql = this.knex(dbTableName)
  .whereRaw('?? = ?', [dbFieldName, ''])
  .update({ [dbFieldName]: null })   // '' ⇒ NULL normalization
```

**Flow:** Check verifies `__id` has a unique index (table identity contract) plus every `unique:true` field; fix branches on ID PREFIX — `__` system columns use default naming, `fld` fields derive the SAME deterministic name the DDL path uses so re-runs converge. Empty-string check counts exact `''` matches per eligible text column; fix NULLs them in one UPDATE.
**Invariant:** Index naming must MATCH the canonical DDL naming (`getFieldUniqueKeyName`) or repairs create duplicate-index drift. `''`→NULL exists because teable treats empty text as absent everywhere downstream (blank buckets, required checks) — keeping '' would fork blank semantics between repaired and never-broken tables. Computed fields are excluded from both scans (their columns are derived).
**Probe:** `grep -cF "startsWith(IdPrefix.Field)" apps/nestjs-backend/src/features/integrity/unique-index.service.ts` → 1; `grep -cF "''" apps/nestjs-backend/src/features/integrity/link-integrity.service.ts` → ≥2 in checkEmptyString.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "checkUniqueIndex fixUniqueIndex getFieldUniqueKeyName", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt prefix-branched index rebuild with canonical naming + conservative ''-to-NULL sweep on non-computed text; adapt naming helper; omit the `__id` special case if your PK differs.
