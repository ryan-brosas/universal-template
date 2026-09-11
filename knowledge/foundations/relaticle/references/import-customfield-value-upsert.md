<!-- capsule-v2 -->
# Buffered custom-field value upsert — dual-write bridge with merge-on-update

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you write EAV-style custom-field values in bulk during import while keeping the model-side attribute bridge and multi-choice merge semantics consistent?

## pendingCustomFieldValues buffer → chunked upsert
**Path/Symbol:** `packages/ImportWizard/src/Jobs/ExecuteImportJob.php`: `collectCustomFieldValues()` (:348-409), `flushCustomFieldValues()` (:458-484), `mergeWithExistingMultiChoiceValues()` (:415-456), `extractCustomFieldData()` (:661-676).
**Signature:** `flushCustomFieldValues(): void` — upsert over unique key `[entity_type, entity_id, custom_field_id, tenantKey]`, update columns = all 8 typed value columns.
**Data Shape:** Each buffered row carries ALL typed columns nulled (`string_value`…`datetime_value`) plus exactly one filled: `CustomFieldValue::getValueColumn($cf->type)`; JSON columns store `json_encode($safeValue)`. ULID string PKs.

### Decisive source
```php
$deduplicated = [];
foreach ($this->pendingCustomFieldValues as $row) {
    $key = $row['entity_type'].'|'.$row['entity_id'].'|'.$row['custom_field_id'].'|'.$row[$tenantKey];
    $deduplicated[$key] = $row;                       // last write wins per entity+field
}
foreach (array_chunk(array_values($deduplicated), 500) as $chunk) {
    DB::table($table)->upsert($chunk, $uniqueBy, $updateColumns);
}
```
And the deliberate blank-date carve-out: "SafeValueConverter passes string-backed types through untouched, and PostgreSQL rejects a blank string for a date/timestamp column" ⇒ `if (is_string($safeValue) && blank($safeValue) && ...isDateOrDateTime()) $safeValue = null;` — pinned by tests :1388 (blank date stored as null) and :1444 (whitespace-only date).

**Flow:** row tx: prefix-strip `custom_fields_` keys out of the payload → per value: format-aware convert (date/number/choice resolution) → multi-choice on UPDATE merges with existing (pending-buffer first, DB fallback) instead of replacing → tag-type values accumulate for option promotion AFTER flush → buffer flushed once per chunk via dedup+upsert. Auto-created related records push their matcher CF value into the SAME buffer (:1051-1066).
**Invariant:** Create vs Update asymmetry is mandatory: create writes the carried value as-is; update MERGES multi-choice arrays (array_unique over existing+new) but scalar columns overwrite. The dedup map must precede chunking or the same entity+field appears twice in one INSERT batch.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:2125/:2163/:2197 merge family, :1320/:1354 update/clear, :2403 option promotion, :2428 case-insensitive dedup).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "collectCustomFieldValues flushCustomFieldValues mergeWithExistingMultiChoiceValues upsert", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt buffer→dedup→chunk-upsert for bulk EAV writes, the all-columns-null-except-one row shape, and the create-overwrite/update-merge asymmetry. Adapt column names and the SafeValueConverter boundary to your stack. Omit Filament's importer() attribute bridge internals (vendor package). Rich direct-test coverage including the Postgres blank-string trap.
