<!-- capsule-v2 -->
# ExecuteImportJob resumable chunk pipeline — how does a 3-try queued import survive crashes without duplicating records or losing counts?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** what is the checkpointing discipline that makes row processing idempotent across job retries?

## Persisted processed-flag + counted-last + failure-path flushes
**Path/Symbol:** `packages/ImportWizard/src/Jobs/ExecuteImportJob.php` (`handle` :100-181, `processRow` :217-326, `flushProcessedRows` :516-535, `failed` :183-206). Job attributes: `#[Backoff([10, 30])] #[Timeout(300)] #[Tries(3)]`, queue `imports`, tenant guard `$import->team_id !== $this->teamId → return`.
**Signature:** `handle(): void`; per-row `processRow(ImportRow $row, BaseImporter $importer, Collection $fieldMappings, ... , array &$results, array $existingRecords = []): void`
**Data Shape:** resume cursor lives IN the store: `import_rows.processed boolean DEFAULT false`. Counters seed from the Import model's persisted columns (`created_rows`, …), not from zero. Side-collections: `$failedRows` (row/error/data triples → failed_import_rows table), `$pendingCustomFieldValues` (batched upsert rows), `$pendingTagOptions`.

### Decisive source
```php
$results = [
    'created' => $import->created_rows,   // counters RESUME from persisted totals
    ...
];
$store->query()->where('processed', false)->orderBy('row_number')
    ->chunkById(500, function (Collection $rows) ... : void {
        foreach ($rows as $row) {
            $this->processRow($row, ...);
            $this->flushProcessedRows($store);   // stamp processed=true after EACH row
        }
        $this->flushCustomFieldValues();  // 500-chunk upsert on unique key
        $this->flushTagOptions();
        $this->flushFailedRows($import);  // 100-chunk insert
        $this->persistResults($import, $results);
    });
...
// Counted last. A rollback undoes the record but not a PHP counter, so
// incrementing before the custom-field pass could report a row as created
// that the database no longer holds.
$results[$isCreate ? 'created' : 'updated']++;
```
and the catch path:
```php
} catch (\Throwable $e) {
    $this->flushFailedRows($import);
    $this->persistResults($import, $results);
    $import->update(['status' => ImportStatus::Failed]);
    try { $this->notifyUser($import, $results, failed: true); } catch (\Throwable) {}
    throw $e;   // rethrow so Tries/Backoff still govern
}
```

**Flow:** load Import → verify team ownership → `ImportStore::load` (missing store ⇒ quiet return) → `ensureProcessedColumn()` self-heals schema on legacy stores → resolve timezone/format maps ONCE → chunk through unprocessed rows in row_number order; each row runs inside its own `DB::transaction` (one bad row fails alone, is recorded to failed_rows, and does NOT abort the run); after every row the processed flag is flushed so a mid-chunk crash resumes at the next unprocessed row; per-chunk side-effect flushes keep memory bounded; final status Completed + notification. The `failed()` hook marks status Failed only if not already terminal.
**Invariant:** progress is durable at row granularity BEFORE the next row starts; counters are monotonic because they are incremented last inside each row's transaction and re-seeded from persisted totals on retry. A row-level exception never escapes the loop — only infrastructure failures do, and they leave partial results + Failed status + user notification behind.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:110 create people, :234 update, :281 skip rows, :340 withheld cells skipped, :370 null match_action tolerated, :415 Failed status on exception, :454 chunked processing, :497 dedup of auto-created companies, :608 vanished update-target skipped).
**Coverage caveat:** none beyond standard best-effort.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ExecuteImportJob processRow flushProcessedRows persistResults", limit: 8, fields: ["signature", "lines"] });
```

## Verdict
Adopt: the whole checkpoint discipline for any queued bulk writer — persisted per-unit done-flag, per-item transaction, counter-increment-after-commit, side-collection flushes at chunk boundaries, failure path that persists evidence then rethrows. Adapt chunk sizes and store medium. Omit nothing; this shape is the capsule.
