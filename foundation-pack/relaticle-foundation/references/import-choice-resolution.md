<!-- capsule-v2 -->
# Choice value resolution — name, case-folded name, existing ID, or pass-through

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** When a CSV cell says "Hot Lead" but a select field stores option IDs, what is the full resolution ladder — and what happens to unknown values?

## resolveChoiceValue / resolveMultiChoiceValue
**Path/Symbol:** `packages/ImportWizard/src/Jobs/ExecuteImportJob.php`: `resolveChoiceValue()` (:750-773), `resolveMultiChoiceValue()` (:778-793).
**Signature:** `resolveChoiceValue(CustomField $cf, string $value): int|string`
**Data Shape:** Options pre-loaded per field (`$cf->options`); result keyed by whether the option model uses string keys (`CustomFields::optionModelUsesStringKeys()`).

### Decisive source
```php
$option = $cf->options->firstWhere('name', $value);                    // exact
if (! $option) {
    $option = $cf->options->first(                                     // case-insensitive
        fn (CustomFieldOption $opt): bool => mb_strtolower((string) $opt->name) === mb_strtolower($value)
    );
}
if ($option) { return CustomFields::optionModelUsesStringKeys() ? (string) $key : $key; }
$isExistingId = $cf->options->contains(fn ($opt): bool => (string) $opt->getKey() === $value);
if ($isExistingId) { return CustomFields::optionModelUsesStringKeys() ? $value : (int) $value; }
return $value;                                                          // pass-through
```
Multi-choice: `array_map(trim(...), explode(',', $value))`; arbitrary-value fields skip resolution entirely and keep raw strings (:782-784).

**Flow:** exact-name → mb-casefolded-name → existing-option-ID (type-normalized) → raw pass-through. Pass-through is NOT an error: unknown-but-non-arbitrary values later fail loudly at validation (`Rule::in` over real option IDs in ValidCustomFields) or get promoted when the field allows it — the executor never invents options for closed choice fields.
**Invariant:** The ID branch must type-cast according to the option model's key type, not assume ints; arbitrary-value fields (tags/email/phone) must bypass ID resolution so their strings survive.
**Probe:** `tests/Feature/ImportWizard/Jobs/ExecuteImportJobTest.php` (:1236 name→ID, :1520 case-insensitive name, :1539 value already an ID, :1255 multi-select names→IDs, :1558 mixed names+IDs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "resolveChoiceValue resolveMultiChoiceValue optionModelUsesStringKeys", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-rung ladder with key-type-aware casting; treat pass-through as deferred-to-validation rather than silent corruption. Adapt the option-model introspection call. Omit vendor CustomFields facade. Direct tests pin each rung.
