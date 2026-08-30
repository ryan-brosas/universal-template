<!-- capsule-v2 -->
# Import key-presence semantics — carried-empty vs withheld vs absent

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you distinguish "the reviewer withheld this cell" from "the cell was empty" from "the column wasn't mapped" when a CSV row becomes a write payload?

## Withhold gate + required-field assertion
**Path/Symbol:** `packages/ImportWizard/src/Store/ImportRow.php`: `getFinalValue()` (:278-289), `isValueWithheld()` (:297-304); `packages/ImportWizard/src/Jobs/ExecuteImportJob.php`: `buildDataFromRow()` (:647-655), `assertRequiredFieldsPresent()` (:623-636).
**Signature:** `isValueWithheld(string $column): bool`; `buildDataFromRow(ImportRow $row, Collection $fieldMappings): array`
**Data Shape:** Row state columns: `raw_data` (Collection), `corrections` (?Collection), `skipped` (?Collection), `validation` (?Collection). `getFinalValue` precedence: withheld→null, corrections.has(col)→correction, else raw.

### Decisive source
```php
/**
 * Emit a key only for a mapped column whose cell the row actually carried, so that key
 * presence downstream means "carried" and a blank value means "carried empty" rather
 * than "withheld". Without the reject, a skipped or errored cell would arrive as null
 * and read as an instruction to clear the field.
 */
return $fieldMappings
    ->reject(fn (ColumnData $mapping): bool => $row->isValueWithheld($mapping->source))
    ->mapWithKeys(fn (ColumnData $mapping): array => [
        $mapping->target => $row->getFinalValue($mapping->source),
    ])
    ->all();
```
And the create-only required guard: `if (is_string($value) ? trim($value) === '' : blank($value)) throw new MissingRequiredFieldException($field->label);` — enforced ONLY on create; "an update legitimately carries a partial payload — a blank cell there means 'leave this column alone', not 'erase the name'" (:609-618 docblock).

**Flow:** validate/review steps write per-column error/skip markers into row JSON → executor REJECTS withheld mappings so their keys never enter `$data` → correction overrides raw for carried cells → update path additionally `array_filter($prepared, filled(...))` and unsets tenancy keys → create path asserts required mapped fields are non-blank BEFORE writing.
**Invariant:** Key presence in the built payload must mean "this column was carried"; null must mean "carried empty", never "withheld". Required-field blanks fail the ROW on create but are silently ignored on update.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:340 skipped values, :1300 blank-on-create is carried not skipped, :1463 skipped cell leaves existing value untouched, :2599 empty required field fails row).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ImportRow isValueWithheld getFinalValue buildDataFromRow", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way semantics (withheld / carried-empty / absent) as a universal import/review contract — it prevents the classic "blank cell erased my data" bug. Adapt the storage medium (JSON row columns here) and marker names. Omit Filament's review UI. Direct tests pin all four quadrants including the whitespace-date edge.
