<!-- capsule-v2 -->
# Create-tool provenance — stamp CreationSource at the action boundary and make schema discovery part of the tool contract

**Source:** relaticle AGPL-3.0 `main@6e3bf8df`; direct-read fallback (MCP graph absent this session). **Question:** How do you route AI-created records through the SAME actions as the web UI while keeping them attributable and schema-valid?

## BaseCreateTool + ValidCustomFields + CreationSource
**Path/Symbol:** `app/Mcp/Tools/BaseCreateTool.php` (whole, 75L): `schema()` (:43-52), `handle()` (:54-74); rule `app/Rules/ValidCustomFields.php` (whole, 80L read): `toRules()` (:27-56), `validate()` (:58-80); enum `app/Enums/CreationSource.php` (whole, 70L): WEB/SYSTEM/IMPORT/API/MCP/CHAT; update twin `app/Mcp/Tools/BaseUpdateTool.php` (whole, 110L).
**Signature:** `BaseCreateTool::handle(Request): Response` — `denyIfTokenCannot('create')` → merge `entityRules($user)` + `ValidCustomFields::toRules(...)` → `$request->validate($rules)` → `$action->execute($user, $validated, CreationSource::MCP)` → resource serialize with `loadMissing('customFieldValues.customField.options')`.
**Data Shape:** Tool schema = entity fields + `custom_fields` object; the schema description itself instructs: "You MUST first read the crm-schema resource to discover valid field codes for this entity type. Unknown field codes will be rejected." Validation output = Laravel rule arrays incl. per-field + per-item (`*`) + choice-option rules from the CustomFields package's ValidationService.

### Decisive source
```php
$model = $action->execute($user, $validated, CreationSource::MCP);
```
```php
$knownCodes = CustomField::query()
    ->withoutGlobalScopes()
    ->where('tenant_id', $this->tenantId)
    ->where('entity_type', $this->entityType)
    ->active()
    ->pluck('code')
    ->all();
```
Provenance is stamped at the action boundary as an explicit argument — never inferred later; the test suite pins `creation_source === MCP` for all five entities. `ValidCustomFields` resolves the tenant's ACTIVE definitions per entity type (codes are unique per entity, not globally) and fails any submitted key outside the known set; update passes `isUpdate: true`.

**Flow:** token-ability gate → two-layer validation merge (entity rules + custom-field rules with unknown-code rejection) → the SAME action class the web UI calls, with the source enum as the provenance carrier → eager-load custom-field relations for the response. Attach/detach twins require at least one relationship array, policy-check `update` on the host record, and use tenant-scoped relationship rules (cross-team ids rejected with `company_ids.0` errors).
**Invariant:** AI writes must flow through the same action/validation path as human writes (one source of behavioral truth) with provenance as an explicit enum argument; unknown custom-field codes must be REJECTED, not silently dropped — the model was told the codes exist in the schema resource.
**Probe:** `tests/Feature/Mcp/McpToolFeaturesTest.php` (creation_source=MCP ×5 entities, required-field + 255-char limits, custom-field create/update, cross-team attach/detach rejection), `tests/Feature/Mcp/RelaticleServerTest.php` (FK existence errors for company_id/contact_id).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "BaseCreateTool ValidCustomFields CreationSource MCP entityRules", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt shared-action delegation with an explicit provenance enum and schema-resource-first tool descriptions for any AI write surface over a validated domain. Adapt the enum cases and the custom-field validation service to your domain. Omit the Laravel rule-object mechanics. Direct tests pin provenance, validation, and tenant scoping across all entities.
