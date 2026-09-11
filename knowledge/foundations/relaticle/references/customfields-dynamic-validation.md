<!-- capsule-v2 -->
# Dynamic validation-rule compilation — rules-as-data over tenant field definitions

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you validate a free-form `custom_fields` map (unknown keys, per-type rules, option membership) when the field set is user-defined at runtime?

## ValidCustomFields rule object
**Path/Symbol:** `app/Rules/ValidCustomFields.php` (whole, 168L): `toRules()` (:30-61), `validate()` (:68-91), `addChoiceFieldOptionRules()` (:102-132), `resolveCustomFields()` (:138-167).
**Signature:** `__construct(string $tenantId, string $entityType, bool $isUpdate = false)`; `toRules(mixed $submittedFields = null): array<string, array<int, mixed>>`
**Data Shape:** Returns Laravel rules array: base `'custom_fields' => ['sometimes','array',$this]`, plus per-code `"custom_fields.{code}"` / `"custom_fields.{code}.*"` entries from the vendor ValidationService, plus injected `Rule::in(optionIds)` for closed choice fields.

### Decisive source
```php
if ($this->isUpdate) {
    if ($submittedCodes === []) { return new EloquentCollection; }        // update: only touched fields
    return $baseQuery->whereIn('code', $submittedCodes)->get();
}
if ($submittedCodes === []) {
    return $baseQuery->whereJsonContains('validation_rules', [['name' => 'required']])->get();  // create: required set
}
return $baseQuery->where(fn (Builder $q) => $q->whereIn('code', $submittedCodes)
    ->orWhereJsonContains('validation_rules', [['name' => 'required']]))->get();
```
Unknown-key rejection is a separate rule pass: submitted keys minus active-field codes ⇒ single aggregated failure `"Unknown custom field keys: a, b."` — queried with `withoutGlobalScopes()` + explicit tenant/entity/active filters.

**Flow:** construct once per request with tenancy context → merge into any rules array → compile-time expansion pulls each definition's type rules AND item-level (`.*`) rules → choice fields get `Rule::in` appended to scalar or item rules (skipping arbitrary-value and lookup-type fields) → at runtime the object rule itself rejects unknown codes.
**Invariant:** Create vs Update scoping differs fundamentally — an update with no CF keys must validate NOTHING (empty payload = untouched), while a create must pull REQUIRED definitions even if the client omitted them entirely.
**Probe:** `tests/Feature/Mcp/Filters/CustomFieldFilterTest.php` sibling suite; API surface `tests/Feature/Api/V1/CustomFieldsApiTest.php`; chat tool suites exercise the rule through CreateCompanyTool paths. No dedicated ValidCustomFields unit file at this pin (caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ValidCustomFields toRules addChoiceFieldOptionRules resolveCustomFields", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt rules-as-data compilation from runtime definitions with the three-way scope selection and the separate unknown-keys pass. Adapt the JSON containment query to your DB. Omit vendor ValidationService internals. Coverage caveat recorded (no isolated unit file).
