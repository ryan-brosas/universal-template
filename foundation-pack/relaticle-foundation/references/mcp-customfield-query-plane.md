<!-- capsule-v2 -->
# Typed custom-field filtering & sorting for AI queries — schema generation with cache invalidation

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you let an AI filter/sort entities by user-defined fields safely — typed operator schemas, EAV joins, and fresh-after-create discovery?

## CustomFieldFilterSchema + CustomFieldFilter + CustomFieldSort
**Path/Symbol:** `app/Mcp/Schema/CustomFieldFilterSchema.php` (whole, 152L): `build()` (:42-62), `operatorsForType()` (:77-99), `resolveFilterableFields()` (:136-151), `forget()` (:123-126); `app/Mcp/Filters/CustomFieldFilter.php` (whole, 104L); `app/Mcp/Filters/CustomFieldSort.php` (whole, 77L).
**Signature:** `build(User $user, string $entityType): array<string,{type:'object',description,properties}>`; filter invokable: `(Builder $query, mixed $value, string $property): void`.
**Data Shape:** Operators per type: numeric family {eq,gt,gte,lt,lte}, strings {eq,contains}, booleans {eq}, multi {has_any}; selects add `in`. Excluded from filtering: FILE_UPLOAD, RECORD, TEXTAREA, RICH_EDITOR, MARKDOWN_EDITOR, and any `settings->encrypted` field.

### Decisive source
```php
abort_if(count($fieldCodes) > self::MAX_CONDITIONS, 422, 'Maximum 10 filter conditions allowed.');
...
$query->whereHas('customFieldValues', function (Builder $q) use ($field, $valueColumn, $operator, $operand): void {
    $q->where('custom_field_id', $field->getKey());
    match ($operator) {
        'eq','gt','gte','lt','lte' => $q->where($valueColumn, self::OPERATOR_MAP[$operator], $operand),
        'contains' => $q->where($valueColumn,'ILIKE','%'.str_replace(['\\','%','_'],['\\%','\%','\_%'...]).'%'),
        'in' => $q->whereIn($valueColumn, (array) $operand),
        'has_any' => $q->whereJsonContains($valueColumn, $operand),
        default => null,                       // unknown operator silently ignored
    };
});
```
Sort = correlated subquery: `CustomFieldValue::query()->select($valueColumn)->whereColumn('entity_id', table.'.id')->where('entity_type', morphClass)->where('custom_field_id', ...)->limit(1)` fed to `orderBy`. Schema memoized 60s per tenant+entity with an explicit invalidation hook: "the TTL is long enough that a missed invalidation reads as 'that field doesn't exist' right after the assistant created it" (:119-122).

**Flow:** schema built from ACTIVE, non-excluded, non-encrypted definitions → published as the tool's `filter` object schema so the model self-documents valid operators → runtime filter resolves codes against the SAME tenant/entity scope (unknown codes skipped silently) → each condition is its own whereHas on the typed value column → AppServiceProvider observes definition saves and calls `Schema::forget(tenant, entity)` on create/update/delete.
**Invariant:** Filterability must exclude encrypted and long-form fields; the sort subquery must pin BOTH entity_type and custom_field_id or cross-field rows leak into ordering; every definition write path must invalidate the memo or the assistant gaslights the user.
**Probe:** `tests/Feature/Mcp/Filters/CustomFieldFilterTest.php`, `CustomFieldSortTest.php`, `SchemaResourcesTest.php`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CustomFieldFilterSchema build operatorsForType CustomFieldFilter applyCondition CustomFieldSort", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt generate-schema-from-definitions + operator whitelisting + correlated-subquery sorting + write-path invalidation as a bundle — each piece fails without the others. Adapt ILIKE vs LIKE to your driver. Omit the CRM type enum mapping. Direct tests cover both filters.
