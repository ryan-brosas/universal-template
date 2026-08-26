<!-- capsule-v2 -->
# Importer timezone anchoring — naive CSV datetimes land where the form would put them

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** In which timezone should a timezone-naive CSV datetime be interpreted so an imported value equals the same string typed into a form?

## importerTimezone resolved once in handle()
**Path/Symbol:** `packages/ImportWizard/src/Jobs/ExecuteImportJob.php`: field decl + docblock (:86-91), resolution (:116), consumption in `convertCustomFieldValue()` (:699-731); date parsing via `DateFormat::parse($value, $isTimestamp, $this->importerTimezone)`.
**Signature:** `$this->importerTimezone = $import->user?->effectiveTimezone() ?? (string) config('app.timezone');`
**Data Shape:** Output formats pinned post-parse: DATE → `Y-m-d`, DATE_TIME → `Y-m-d H:i:s`; unparseable ⇒ `UnparsableDateException` (row fails, never silently nulled).

### Decisive source
```php
/**
 * Zone the CSV's naive datetimes are interpreted in — the importer's own, so an
 * imported value lands on the same instant as the same string typed into the form.
 * Resolved once in handle() because the job runs on the queue with no session.
 */
private string $importerTimezone = 'UTC';
```
And the failure-honesty comment (:717-726): "An unparseable date used to be returned as-is, which the SafeValueConverter then blanked to null: the row imported, the value vanished, and the summary still said '0 failed'. Silently dropping data the user handed us is worse than refusing the row."

**Flow:** job boots (queue context, no auth session) → resolve importer's effective tz ONCE from its User record, config fallback → per-cell parse passes tz into the format parser → whitespace-only cells short-circuit BEFORE the parser (blank means "no value", not garbage) → parsed values formatted to storage strings; failures raise and route to the failed-row ledger with column name + offending value.
**Invariant:** The tz must be captured at job start (not per row) and must come from the importing USER's setting — using UTC or the server zone shifts every imported datetime relative to what the app's own forms write.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:2515 datetime matches form-stored instant, :2542 date-only NOT shifted for foreign-tz importer, :2568 unparseable fails the row).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "importerTimezone convertCustomFieldValue UnparsableDateException DateFormat", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "interpret naive timestamps in the acting user's zone, resolved once in the worker" for any queue-side date ingestion. Adapt the user-setting accessor. Omit vendor DateFormat enum specifics. Direct tests pin all three polarities including the regression this code was written to fix.
