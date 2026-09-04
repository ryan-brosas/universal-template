<!-- capsule-v2 -->
# Import failure ledger — per-row error capture with bounded persistence

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you record which rows failed and why, so a 10k-row import reports precisely instead of dying on the first bad cell?

## recordFailedRow / flushFailedRows + failed() handler
**Path/Symbol:** `packages/ImportWizard/src/Jobs/ExecuteImportJob.php`: `recordFailedRow()` (:564-571), `flushFailedRows()` (:584-607), catch block (:321-325), `failed()` (:183-206).
**Signature:** `recordFailedRow(int $rowNumber, array $rawData, \Throwable $e): void` — error message clamped via `Str::limit($e->getMessage(), 500)`.
**Data Shape:** `failed_rows` table: ULID id, import_id, team_id, data (raw CSV row JSON), validation_error, timestamps; inserted in chunks of 100.

### Decisive source
```php
} catch (\Throwable $e) {
    $results['failed']++;
    $this->recordFailedRow($row->row_number, $row->raw_data->all(), $e);
    report($e);
}
```
And the terminal handler's state guard (:191-193): only flips status to Failed when the import is NOT already Completed/Failed — a retried job whose successor succeeded must not retro-fail the import.

**Flow:** any per-row throwable → counter++ → buffered ledger entry (clamped message, full raw data preserved for re-download/correction) → report() to error tracking but NOT rethrown → flush at chunk end AND in the exception path of handle() → queue-level exhaustion invokes `failed()` which still persists rows + notifies before giving up.
**Invariant:** A row failure must be isolated (never aborts the chunk), journaled with its ORIGINAL data (not the partially-built payload), and flushed on BOTH success-path-chunk-end and job-failure paths; notification send is itself try/caught so a broken mailer can't mask the real error.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:690 persisted details, :753/:774+ unicode rows, :943 exhausted retries, :415 status Failed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "recordFailedRow flushFailedRows FailedImportRow report", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt buffer→bounded-flush failure ledgers with original-data capture and dual-path flushing. Adapt clamp length and chunk size. Omit Filament review rendering. Direct tests pin persistence, unicode safety, and retry-exhaustion.
