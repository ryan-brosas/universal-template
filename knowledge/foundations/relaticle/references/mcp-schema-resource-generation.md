<!-- capsule-v2 -->
# Schema-resource generation — per-entity JSON schemas assembled from one cached tenant-aware resolver

**Source:** relaticle AGPL-3.0 `main@6e3bf8df`; direct-read fallback (MCP graph absent this session). **Question:** How do you give an AI client a live, tenant-specific schema document for each entity — including user-defined fields — without the document drifting from what the write tools will actually accept?

## TaskSchemaResource + ResolvesEntitySchema + CrmOverviewPrompt
**Path/Symbol:** `app/Mcp/Resources/TaskSchemaResource.php` (whole, 97L): `shouldRegister()` (:24-32), `handle()` (:34-96); trait `app/Mcp/Resources/Concerns/ResolvesEntitySchema.php` (whole, 113L): `resolveCustomFields()` (:20-38), `resolveFilterableFields()` (:40-44), `CHOICE_TYPES` (:46), `formatCustomFields()` (:52-83), `fieldFormatHint()` (:89-108); prompt `app/Mcp/Prompts/CrmOverviewPrompt.php` (whole, 79L): `shouldRegister()` (:24-32), `handle()` (:38-77, `CACHE_TTL = 60` at :21).
**Signature:** `resolveCustomFields(User $user, string $entityType): array<string, {name, type, required, input_format?, example?, options?}>`; resource `handle(Request $request): Response` returning `Response::text(json_encode($schema, JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR))`.
**Data Shape:** Static per-entity blocks (`fields`, `relationships`, `writable_relationships` with omit-vs-`[]`-removes semantics, `aggregate_includes`, `usage`) merged with DYNAMIC blocks: `custom_fields` (keyed by field code, options as `{id, label}` pairs for the five choice types) and `filterable_fields` (delegated to `CustomFieldFilterSchema::build`).

### Decisive source
```php
return Cache::remember($cacheKey, 60, function () use ($teamId, $entityType): array {
    $fields = CustomField::query()
        ->withoutGlobalScopes()
        ->where('tenant_id', $teamId)
        ->where('entity_type', $entityType)
        ->active()
        ->select('id', 'code', 'name', 'type', 'validation_rules')
        ->with(['options:id,custom_field_id,name'])
        ->get();
```
The dynamic half is cached 60s per `team+entity` (`custom_fields_schema_{teamId}_{entityType}`) and reads ACTIVE definitions with `withoutGlobalScopes()` — the tenant filter is explicit because the query must survive the global-scope-free context MCP runs in. `required` is derived by scanning `validation_rules` for a rule named `required`, not a column. Per-type `input_format`/`example` hints come from a `match` over the field type (link/email/phone are ARRAYS of strings; select/radio take one option ID; multi-select families take arrays of option IDs; date_time is ISO 8601). The sibling prompt caches a per-team overview TEXT (`crm_overview_{teamId}`, 60s TTL) — counts plus five latest company/people names — so an agent can orient before any tool call. Both resource and prompt gate registration on token ability: a Sanctum PAT must `can('read')`, while non-PAT callers (OAuth tokens, web) register unconditionally.
**Flow:** client reads `relaticle://schema/{entity}` → static contract + cached dynamic custom-field/filter blocks → the tool schema descriptions ("read the crm-schema resource first") steer the model here BEFORE any write → write tools re-validate against the same live definitions, so a stale cached schema cannot cause an accepted-but-wrong write (unknown codes are rejected at the tool).
**Invariant:** The schema document must be derivable from the same tenant-scoped ACTIVE definitions the validators use; per-type input-format hints must match what the write path accepts (array vs scalar for choice families); a read-gated token must not even see the resource registered.
**Probe:** `tests/Feature/Mcp/SchemaResourcesTest.php` (all five entities render with entity key + static fields; a created `test_field` appears in the company schema output).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ResolvesEntitySchema resolveCustomFields TaskSchemaResource shouldRegister CrmOverviewPrompt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt schema-as-resource with a cached tenant-aware resolver feeding the dynamic half and static write-contract blocks kept in code. Adapt the cache TTL/invalidation story to your definition-write paths (this repo invalidates the FILTER schema on definition saves; the schema-resource cache rides the 60s TTL). Omit the Laravel MCP attribute/registration mechanics. Direct tests pin all five entity schemas plus dynamic-field inclusion; the 60s staleness window is covered by the filter-schema invalidation hook, not a dedicated test — caveat recorded.
