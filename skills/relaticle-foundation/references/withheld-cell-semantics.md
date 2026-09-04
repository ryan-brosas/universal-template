<!-- capsule-v2 -->
# Withheld-cell semantics — how does "reviewer skipped this cell" stay different from "the cell was empty"?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** how are three cell states (raw value / correction / withheld) collapsed into one write-time truth without erasing data?

## Key-presence contract built by rejecting withheld mappings
**Path/Symbol:** `packages/ImportWizard/src/Store/ImportRow.php:getFinalValue/isValueWithheld` (:278-304) + `packages/ImportWizard/src/Jobs/ExecuteImportJob.php:buildDataFromRow` (:647-655) + `assertRequiredFieldsPresent` (:623-636).
**Signature:** `ImportRow::getFinalValue(string $column): mixed` (correction > raw, null when withheld); `isValueWithheld(string $column): bool` (skipped OR has validation error); `buildDataFromRow(ImportRow $row, Collection $fieldMappings): array`.
**Data Shape:** per-row JSON columns `corrections` (map col→fixed value), `skipped` (map col→true), `validation` (map col→error). Downstream `$data` is a sparse map whose KEY PRESENCE means "carried".

### Decisive source
```php
/**
 * Emit a key only for a mapped column whose cell the row actually carried, so that key
 * presence downstream means "carried" and a blank value means "carried empty" rather
 * than "withheld". Without the reject, a skipped or errored cell would arrive as null
 * and read as an instruction to clear the field.
 */
private function buildDataFromRow(ImportRow $row, Collection $fieldMappings): array
{
    return $fieldMappings
        ->reject(fn (ColumnData $mapping): bool => $row->isValueWithheld($mapping->source))
        ->mapWithKeys(fn (ColumnData $mapping): array => [
            $mapping->target => $row->getFinalValue($mapping->source),
        ])->all();
}
```
Paired with update-side filtering:
```php
if (! $isCreate) {
    unset($prepared['team_id'], $prepared['creator_id'], $prepared['creation_source']);
    $prepared = array_filter($prepared, filled(...));   // blank ⇒ leave column alone
}
```
And required-field enforcement (create-only):
```php
// Only enforced on create. An update legitimately carries a partial payload — a blank
// cell there means "leave this column alone", not "erase the name".
```

**Flow:** reviewer marks a cell skipped or leaves it errored → `isValueWithheld` true → the mapping is REJECTED before mapping, so no key exists downstream → create path: missing required key throws MissingRequiredFieldException (blank-string check via trim) → update path: absent keys never touch their columns; present-but-blank values are filtered by `filled()` so an explicit empty cell also leaves data intact unless truly carried.
**Invariant:** `null`/absence NEVER means "clear the target" on update — clearing requires an explicit carried-empty decision upstream. The same helper answers both questions ("what value?" and "was it withheld?") from one source so callers can't diverge.
**Probe:** `ExecuteImportJobTest.php` (:256 partial-update preserves existing data, :340 "skips individual values marked as skipped").
**Coverage caveat:** none beyond standard best-effort.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "buildDataFromRow isValueWithheld getFinalValue assertRequiredFieldsPresent", limit: 8, fields: ["signature", "lines"] });
```

## Verdict
Adopt: the tri-state cell model and the reject-to-express-absence pattern for any merge/import surface where "no value" must not destroy target data. Adapt state names to your review UI. Omit CRM required-field list specifics.
