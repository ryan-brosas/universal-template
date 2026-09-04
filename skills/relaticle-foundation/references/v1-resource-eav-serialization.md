<!-- capsule-v2 -->
# V1 API resource serialization — conditional attributes, orphan-filtered EAV projection, and id+label choice rendering

**Source:** relaticle AGPL-3.0 `main@6e3bf8df`; direct-read fallback (MCP graph absent this session). **Question:** How do you serialize EAV custom fields and optional aggregates through one JSON:API-style resource layer that both the REST API and the MCP tools consume, without leaking internal columns or orphaned values?

## TaskResource + FormatsCustomFields
**Path/Symbol:** `app/Http/Resources/V1/TaskResource.php` (whole, 55L): `toAttributes()` (:20-36), `toRelationships()` (:39-48); trait `app/Http/Resources/V1/Concerns/FormatsCustomFields.php` (whole, 85L): `formatCustomFields()` (:14-30), `resolveFieldValue()` (:32-44), `resolveSingleChoiceValue()` (:46-62), `resolveMultiChoiceValue()` (:64-81); siblings `CompanyResource`/`PeopleResource`/`OpportunityResource`/`NoteResource`/`UserResource`/`CustomFieldResource` share the shape.
**Signature:** `formatCustomFields(Model $record): \stdClass`; `toAttributes(Request $request): array<string, mixed>`; `toRelationships(Request $request): array<string, class-string<JsonApiResource>>`.
**Data Shape:** Attributes = scalar columns + `custom_fields` object (stdClass → JSON object, empty object when the relation is not loaded) + `*_count` aggregates wrapped in `whenHas()` (present only when the query asked for the count include). Relationships map names to resource classes; the JSON:API envelope (`data`/`attributes`/`relationships`/`included`) is provided by the framework's `JsonApiResource` base.

### Decisive source
```php
$result = $record->getRelation('customFieldValues')
    // Skip orphaned values whose custom field was deleted: the eager-loaded relation is null.
    ->filter(fn (CustomFieldValue $fieldValue): bool => isset($fieldValue->getRelations()['customField']))
    ->mapWithKeys(fn (CustomFieldValue $fieldValue): array => [
        $fieldValue->customField->code => $this->resolveFieldValue($fieldValue),
    ])
    ->all();
return (object) $result;
```
Choice values are never returned as bare option ids: single choice renders `{id, label}` (label falls back to the raw id when the option row is gone), multi choice renders an array of `{id, label}` after filtering to string/numeric entries. Non-choice types pass the raw value through. The orphan filter is the load-bearing line: custom-field values can outlive a deleted definition, and the eager load leaves their `customField` relation null — without the filter the serializer would fatal on `->customField->code`.
**Flow:** action returns model with `customFieldValues.customField.options` eager-loaded → resource projects attributes (custom_fields keyed by code, counts only when `whenHas` sees the aggregate select) and relationships → the SAME resource class is reused by MCP tools (`Response::text(new TaskResource($model->loadMissing(...))->toJson(...))`) so REST and MCP responses cannot disagree. Internal columns (`team_id`, `creator_id` on create responses, `deleted_at`, `creation_source` is kept but `deleted_at` is never emitted) stay out of the payload — the MCP fetch test pins the exact key set.
**Invariant:** The custom_fields object must be `{}` (never `null` or a fatal) when values are not loaded; orphaned values must be skipped, not rendered; choice labels must degrade to raw ids when the option row was deleted; every count attribute must be conditional on the include.
**Probe:** `tests/Feature/Api/V1/TasksApiTest.php` (attribute key set, `custom_fields` type, `missing('team_id')`, count includes, disallowed-include 400), `tests/Feature/Mcp/SearchFetchToolsTest.php` (fetch data envelope: no `deleted_at`, no internal columns).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "FormatsCustomFields formatCustomFields TaskResource toAttributes toRelationships whenHas", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the resource-trait split (per-entity attribute maps + one shared EAV formatter) with orphan filtering and id+label choice projection. Adapt the JSON:API envelope mechanics to your framework. Omit the Laravel `whenHas`/count-include plumbing if your API is not include-driven. Direct tests pin the task API surface and the MCP fetch envelope; the orphan-filter branch itself has no dedicated unit test (it is exercised implicitly by deleted-field fixtures) — caveat recorded.
