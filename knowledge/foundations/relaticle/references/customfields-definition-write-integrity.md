<!-- capsule-v2 -->
# Definition write-path integrity — re-validate at execute, case-asymmetric uniqueness, tenant-swap bracket

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you let an AI assistant (or any non-form caller) create custom-field definitions without breaking the uniqueness and cap invariants the management UI enforces?

## CreateCustomField + CustomFieldDefinitionValidator
**Path/Symbol:** `app/Actions/CustomFields/CreateCustomField.php` (whole, 123L): `execute()` (:60-122); `app/Support/CustomFieldDefinitionValidator.php` (whole, 275L): `forCreate()` (:40-70), `uniqueNameIgnoringCase()` (:161-183), `withinFieldCap()` (:207-221), `normalize()` (:231-249).
**Signature:** `CreateCustomField::execute(User $user, array $data): CustomField`; validator returns normalized+validated array.
**Data Shape:** Closed vocabularies as consts: `ALLOWED_TYPES` (17), `CHOICE_TYPES` (5), `VALID_ENTITY_TYPES` (5). Caps from config: `chat.max_custom_fields_per_entity` (50), `chat.max_field_options` (50).

### Decisive source
```php
$previousTenantId = TenantContextService::getCurrentTenantId();
TenantContextService::setTenantId($teamId);
try {
    // Re-validated here, not just at proposal time: a proposal approved after
    // someone else claimed the name must fail rather than write a duplicate.
    $validated = CustomFieldDefinitionValidator::forCreate($user, $data);
    ...
} finally { TenantContextService::setTenantId($previousTenantId); }
```
Uniqueness asymmetry docblock (:152-158): "Names compare case-insensitively... Codes deliberately stay case-sensitive: they are slug-generated, and the DB's own unique index on (code, entity_type, tenant_id) is case-sensitive too, so a looser rule here would reject values the database would have accepted." Name-uniqueness runs on the QUERY BUILDER, not Eloquent — "so deactivated fields count as taken — the activable global scope would otherwise hide them and let a duplicate through."

**Flow:** owner-only gate (`ownsTeam`, 403 otherwise) → tenant bracket around everything → normalize payload (trim; options reshaped to `[{name}]` whether objects or strings) → validate: entity-in-cap + type-allowlist + ci-name-unique + cs-code-unique + options required/prohibited by type + distinct-ci option names → auto-generate unique code when blank → next sort_order computed with the activable scope REMOVED → transactional create of field + ordered options.
**Invariant:** The same validator must serve proposal pre-flight AND authoritative execution (drift between the two is the attack the docblock describes); every tenant-scoped query inside must run inside the set/restore bracket or the vendor TenantScope no-ops.
**Probe:** `tests/Feature/Chat/CreateCustomFieldToolTest.php`, `UpdateCustomFieldToolTest.php`, `AddCustomFieldOptionsToolTest.php`, `AllCustomFieldsViaChatTest.php` (whole chat-side definition lifecycle).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CreateCustomField execute CustomFieldDefinitionValidator forCreate uniqueNameIgnoringCase", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-shared-validator for proposal+execution, builder-level uniqueness that includes deactivated rows, and the case asymmetry (names CI / codes CS matching the DB index). Adapt config caps and the tenant-context service to your multi-tenancy layer. Omit the Filament FieldForm twin. Direct tests cover the full chat-tool surface.
