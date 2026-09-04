<!-- capsule-v2 -->
# LLM custom-field label bridge — one case-insensitive label→id map feeding both read and write paths

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; Codebase Memory `relaticle`. **Question:** How does an assistant that speaks human option labels ("In progress") safely write and filter typed EAV choice fields?

## Shared option map + validator reuse
**Path/Symbol:** `packages/Chat/src/Services/Tools/CustomFieldOptionMap.php` (whole, 60L); `CustomFieldsRequestValidator.php` (`validate` :28-57, `translateLabels` :79-155); schema-side twin `CustomFieldsSchemaDescriber.php`; display-side twin `CustomFieldsDisplayFormatter.php`.
**Signature:** `CustomFieldOptionMap::fromFields(Collection $fields): array<string, {ids: array<string,string>, labels: list<string>}>` + `idFor(array $entry, string $label): ?string`; `CustomFieldsRequestValidator::validate(User, string $entityType, mixed $raw): CustomFieldsValidationResult{cleanFields, error}`.
**Data Shape:** Map keyed by field code; ids indexed by `mb_strtolower(label)` while `labels` keep stored casing for display. Validator result is either `{cleanFields: <code=>optionId payload>}` or an error string prefixed per record (`"records[2]: custom_fields.stage option \"X\" is not one of the configured choices."`).

### Decisive source
```php
// The one place that answers "which option id does this label mean?".
// The read path (filtering) and the write path (setting a value) both take option
// LABELS from the assistant and both have to reach an option id, and they used to
// do it with two separate lookups that had already drifted: one matched labels
// case-sensitively, the other did not, so the same string could be accepted when
// filtering and rejected when saving.
$ids[mb_strtolower($label)] = (string) $option->getKey();
```
```php
$fields = CustomField::query()->where('tenant_id', $teamId)
    ->where('entity_type', $entityType)->active()
    ->whereIn('code', array_keys($rawCustomFields))->with('options')->get();
$translated = $this->translateLabels($rawCustomFields, $fields);
$rules = new ValidCustomFields($teamId, $entityType, isUpdate: true)->toRules($translated->cleanFields);
if (Validator::make(['custom_fields' => $translated->cleanFields], $rules)->fails()) { ... }
```

**Flow:** tool schema generation calls `SchemaDescriber->describe(team, entityType)` so the model sees the tenant's LIVE field catalog in every tool description → submitted values flow through `translateLabels`: unknown codes pass through untouched (core-field names are not custom fields), non-choice types pass through, arbitrary-value and lookup fields bypass translation, strict choice fields must match a configured label case-insensitively or the whole call returns an error string → cleaned id-keyed payload re-validates through the SAME `ValidCustomFields` rule object the MCP plane uses → clean fields ride into the proposal's action data.
**Invariant:** Label lookup is case-insensitive everywhere because "an option list is not a set of identifiers"; policy differences (arbitrary values, lookups) stay at the CALLER, only the lookup is shared. Validation failures are returned as strings for model self-correction — never exceptions. Multi-choice values must be arrays of translatable labels; single-choice accepts string|int.
**Probe:** `tests/Feature/Chat/AllCustomFieldsViaChatTest.php` — end-to-end label→option-id persistence across all five entities (:50-123), plus the casing matrix "exact/lowercased/uppercased all accepted" (:257-285). Direct unit coverage lives beside it (`CustomFieldsBridge/` test dir).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "translateLabels optionMap idFor ValidCustomFields cleanFields", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared-map pattern whenever two LLM surfaces (read filters, write payloads) must interpret identical human labels identically — the docblock documents the exact drift bug that motivated it. Adapt `ValidCustomFields` to your validation kernel; keep error-as-string semantics so the model can retry. Omit the vendor type-data specifics (`acceptsArbitraryValues`, `lookup_type`).
