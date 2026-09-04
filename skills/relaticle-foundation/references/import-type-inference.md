<!-- capsule-v2 -->
# Column type inference — dynamic-rule voting with a text fallback that means "unknown"

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you guess a CSV column's data type from samples without hardcoding a type table?

## DataTypeInferencer lazy-initialized voting
**Path/Symbol:** `packages/ImportWizard/src/Support/DataTypeInferencer.php` (whole, 224L): `infer()` (:40-84), `initialize()` (:89-121), `extractValidationKey()` (:127-139), `detectType()` (:144-169), `isCurrency()`/`isNumber()` (:190-198).
**Signature:** `infer(array $values): InferenceResult{type: ?string, confidence: float, suggestedFields: array<string>}`
**Data Shape:** Two maps built once from the field-type registry: `$validationToFieldType` (rule key ⇒ type) and `$dataTypeToFieldType` (FieldDataType value ⇒ type); vote pool = union + `'text'`.

### Decisive source
```php
$typeVotes = array_fill_keys(array_unique($allTypes), 0);
foreach ($nonEmptyValues as $value) {
    $type = $this->detectType(trim((string) $value));
    if (isset($typeVotes[$type])) { $typeVotes[$type]++; }
}
...
if ($topType === 'text') {
    return new InferenceResult(type: null, confidence: 0.0, suggestedFields: []);
}
$confidence = $topVotes / $totalVotes;
if ($confidence < 0.5) { return new InferenceResult(type: null, confidence: $confidence, suggestedFields: []); }
```
Detection order is priority: validation-backed types (email/phone/url via Laravel Validator, incl. `'phone:AUTO'` param-strip and regex⇒link special case) → date validator → currency regex (`$€£¥`, optional thousands separators) → numeric-after-`,`/space-strip → text.

**Flow:** first call builds maps by instantiating every registered field type and reading its schema (no hardcoded mapping — "Detection rules and field types are built dynamically from FieldManager") → per non-empty value one detection pass → plurality vote; text-wins or sub-50% confidence returns NULL type (not "text") so callers treat the column as unmapped rather than mis-mapping.
**Invariant:** Empty columns and low-confidence/text outcomes must yield `type: null`; suggested fields are only real configured custom-field codes of the winning type (prefixed for the executor).
**Probe:** No dedicated upstream test file for DataTypeInferencer at this pin (grep over tests/ found none) — coverage caveat; behavior cross-pinned indirectly through ValidateColumnJobTest and MappingStep flows.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "DataTypeInferencer infer initialize detectType typeVotes", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt registry-derived detection rules + majority-vote-with-null-fallback (never guess below 50%). Adapt rule extraction to your validation vocabulary; keep the currency-before-number ordering (else `$1,200` reads as number). Omit CRM field-suggestion queries. Coverage caveat recorded above.
