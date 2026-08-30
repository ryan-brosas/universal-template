<!-- capsule-v2 -->
# Batched custom-field value plane — how do thousands of heterogeneous typed values land exactly-once without N queries?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** what is the accumulate→dedupe→upsert choreography that writes EAV-style custom-field values safely?

## Pending buffer keyed by entity+field+tenant, upserted in 500s
**Path/Symbol:** `packages/Chat/../ImportWizard/src/Jobs/ExecuteImportJob.php:collectCustomFieldValues` (:348-409), `mergeWithExistingMultiChoiceValues` (:415-456), `flushCustomFieldValues` (:458-484), plus tag promotion `accumulateTagOptions` (:487-500)/`flushTagOptions` (:502-509).
**Signature:** `collectCustomFieldValues(Model $record, array $customFieldData, Collection $customFieldDefs, array $customFieldFormatMap = [], bool $isCreate = true): void`; `flushCustomFieldValues(): void`.
**Data Shape:** each pending row carries ALL eight typed value columns nulled except one (`$valueColumn = CustomFieldValue::getValueColumn($cf->type)` ∈ string/text/integer/float/json/boolean/date/datetime); unique-by = `[entity_type, entity_id, custom_field_id, tenantKey]`; json_value arrays json_encoded.

### Decisive source
```php
$deduplicated = [];
foreach ($this->pendingCustomFieldValues as $row) {
    $key = $row['entity_type'].'|'.$row['entity_id'].'|'.$row['custom_field_id'].'|'.$row[$tenantKey];
    $deduplicated[$key] = $row;              // LAST WRITE WINS within one flush
}
foreach (array_chunk(array_values($deduplicated), 500) as $chunk) {
    DB::table($table)->upsert($chunk, $uniqueBy, $updateColumns);
}
$this->pendingCustomFieldValues = [];
```
Blank-date guard:
```php
// SafeValueConverter passes string-backed types through untouched, and PostgreSQL
// rejects a blank string for a date/timestamp column.
if (is_string($safeValue) && blank($safeValue) && $cf->typeData->dataType->isDateOrDateTime()) {
    $safeValue = null;
}
```
Update-merge semantics:
```php
if (! $isCreate && $cf->typeData->dataType === FieldDataType::MULTI_CHOICE && is_array($safeValue)) {
    $safeValue = $this->mergeWithExistingMultiChoiceValues($record, $cf, $safeValue, $tenantKey);
}
```

**Flow:** during each row transaction, values accumulate as pending rows (choice resolution + format-aware date/float parsing happen here; unparsable dates THROW rather than silently vanish) → at chunk end, dedupe by natural key (later rows override earlier ones — matches sequential row order) → one upsert per 500-row chunk → buffer cleared. Multi-choice updates union with existing DB values (checking pending buffer first, then DB) so an update appends tags instead of replacing them. Tag-type fields promote raw strings to options AFTER all rows flush.
**Invariant:** one physical row per (entity, field, tenant) per flush regardless of duplicate touches; the pending-buffer-first merge prevents reading stale DB state for entities touched earlier in the SAME chunk; blank strings never reach date columns.
**Probe:** `ExecuteImportJobTest.php` (:145 sets custom field values, :175 batch JSON query resolution).
**Coverage caveat:** multi-choice merge verified against source + tests listed; Postgres-specific blank-date behavior asserted by comment, exercised only if suite runs pgsql.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "collectCustomFieldValues flushCustomFieldValues mergeWithExistingMultiChoiceValues", limit: 8, fields: ["signature", "lines"] });
```

## Verdict
Adopt: buffer-dedupe-upsert plane for any EAV/bulk-typed-value writer; last-write-wins dedupe aligned with source ordering; typed-column-with-single-fill shape keeps one table serving many types. Adapt the type-column map and choice-resolution ladder to your field system. Omit vendor package specifics (Relaticle/custom-fields config keys).
