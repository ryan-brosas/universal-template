<!-- capsule-v2 -->
# Import executor row loop — when is a row "created" and what happens on failure?

**Source:** relaticle AGPL-3.0 `main@2c2a245605c9012e9cd1de53d2c15de6c816479f`; Codebase Memory `relaticle`. **Question:** How does a queued import execute rows so that counts, processed-markers, and custom-field writes stay consistent across chunked processing and retries?

## Chunked row execution inside ExecuteImportJob
**Path/Symbol:** `packages/ImportWizard/src/Jobs/ExecuteImportJob.php`: `handle()` (:100-181), `processRow()` (:217-326), `preloadExistingRecords()` (:541-561).
**Signature:** `processRow(ImportRow $row, BaseImporter $importer, Collection $fieldMappings, array $allowedKeys, Collection $customFieldDefs, array $customFieldFormatMap, ?MatchableField $matchField, ?string $matchSourceColumn, array $context, array &$results, array $existingRecords = []): void`
**Data Shape:** `$results = ['created'=>int,'updated'=>int,'skipped'=>int,'failed'=>int]` seeded from the persisted `Import` model then mutated by reference through `chunkById(500, ...)`. Per-row state lives in job fields: `$processedRows`, `$dedupedRows`, `$failedRows`, `$pendingCustomFieldValues`, `$pendingTagOptions`. Queue config via PHP attributes: `#[Backoff([10,30])] #[Timeout(300)] #[Tries(3)]`.

### Decisive source
```php
// Counted last. A rollback undoes the record but not a PHP counter, so
// incrementing before the custom-field pass could report a row as created
// that the database no longer holds.
$results[$isCreate ? 'created' : 'updated']++;
```
The whole DB write (entity-link resolution → `prepareForSave` → CF extraction/prefix strip → update-mode guards → `forceFill`+`save` → deferred CF collection) runs inside one `DB::transaction(...)`; only after it commits does `markProcessed($row)` run (:320).

**Flow:** seed counts from Import model → resolve match field/source column once → `store->query()->where('processed', false)->orderBy('row_number')->chunkById(500, ...)` → per chunk: preload all update-targets in ONE query keyed by stringified PK → per row: skip non-create/update actions → intra-run dedup may PROMOTE Create→Update → transactional write (count incremented LAST inside tx) → mark processed → flush buffers (CF values, tag options, failed rows, results) at chunk end → final Import update + notification; any thrown error flushes failed rows/results, marks Import Failed, notifies, then RETHROWS (so queue retry semantics still see the failure). Update rows whose matched record vanished are counted `skipped`, not failed (:266-271).
**Invariant:** A PHP-side counter must never be incremented before the transaction commits — rollback undoes DB rows but not counters. Every buffer flush is bounded-chunk (500 CF values, 100 failed rows) and resets the buffer, so a retried chunk never double-writes already-`processed` rows.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:370 null-action skip, :608 missing-update-target skip, :882/:901 1000-row chunked runs, :943 exhausted-retries `failed()` handler).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ExecuteImportJob processRow handle", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the count-last-in-transaction rule, the preload-existing-per-chunk map, buffered-then-flushed side tables, and catch-per-row-with-report() isolation (one bad row fails alone; the import continues). Adapt chunk size, attribute-based queue config syntax (Laravel 11+), and the specific `custom_fields_` prefix constant to your host's naming. Omit the Filament notification plumbing and the concrete entity set (product surface). Direct-test coverage is strong upstream (2,617-line suite); the timezone-dependent date path carries its own caveat in the importer-timezone capsule.
