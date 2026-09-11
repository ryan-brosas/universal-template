<!-- capsule-v2 -->
# Relationship expansion — resource-map reflection with aggregate stripping

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you expand `include`-style relations in an AI tool response without hand-writing serializers per relation?

## SerializesRelatedModels trait
**Path/Symbol:** `app/Mcp/Tools/Concerns/SerializesRelatedModels.php` (whole, 90L); consumer loop `app/Mcp/Tools/BaseListTool.php` (:98-122).
**Signature:** `resolveRelationshipMap(string $resourceClass, Model $model): array<string,class-string<JsonApiResource>>`; `serializeRelation(Model $parentModel, string $relation, array $relationshipMap): ?array`.
**Data Shape:** Map derived from the parent JsonApiResource's own `toRelationships(request())`; output items = `{id, ...attributes}`; collections map to arrays, singles to objects, unloaded to null.

### Decisive source
```php
// Strip unloaded aggregate counts (whenHas returns MissingValue -> {})
$attributes = array_filter(
    $attributes,
    fn (mixed $value, string $key): bool => ! str_ends_with($key, '_count') || $model->hasAttribute($key),
    ARRAY_FILTER_USE_BOTH,
);
return ['id' => $model->getKey(), ...$attributes];
```
Consumer-side guards: `$relation === 'customFieldValues'` is skipped (EAV rows are projected into typed attributes elsewhere), the map is resolved lazily ONCE (`$relationshipMap ??=`) and only when at least one loaded relation exists, and unknown-relation fallback is `$model->only(['id','name','title','email'])`.

**Flow:** after resource serialization, iterate each result model's LOADED relations → reflect relationship→resource map off the entity's JsonApiResource → serialize each related item through its own resource's `toAttributes`, prefixing id → strip `_count` keys whose attribute was never actually loaded → attach onto the already-decoded response object.
**Invariant:** Only LOADED relations are expanded (never lazy-load inside a list serializer); aggregates that would render as `{}` must be dropped, not emitted.
**Probe:** exercised across `tests/Feature/Mcp/{CompanyToolsTest,...}Test.php` include paths; no isolated trait unit file (caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "SerializesRelatedModels resolveRelationshipMap serializeRelatedModel toRelationships", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reflection-off-the-existing-API-resource for relation expansion — one source of serialization truth. Adapt to your resource layer's introspection API. Omit Laravel JsonApi specifics. Caveat: covered indirectly via tool suites.
