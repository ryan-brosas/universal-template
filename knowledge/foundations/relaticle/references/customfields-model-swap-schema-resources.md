<!-- capsule-v2 -->
# Model-swap + schema-resource pattern — vendoring a package's data model into app space

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you extend a closed vendor package (final classes, own models) so app-level behavior — observers, scopes, overrides — applies to ITS tables?

## App-level model twins + schema resources
**Path/Symbol:** `app/Models/CustomField.php` (whole, 41L); registration `app/Providers/AppServiceProvider.php` (:440-446); consumers `app/Mcp/Resources/{CompanySchemaResource,...}SchemaResource.php` (five entity-schema resources).
**Signature:** `CustomFields::useCustomFieldModel(CustomField::class); useSectionModel(...); useOptionModel(...); useValueModel(CustomFieldValue::class);`
**Data Shape:** App twin extends the vendor model and adds: ULID keys, `#[ScopedBy([TenantScope, SortOrderScope])]`, `#[ObservedBy(CustomFieldObserver)]`, plus domain methods like `promotesValuesToOptions()`.

### Decisive source
```php
// Use custom models for custom-fields package
CustomFields::useCustomFieldModel(CustomField::class);
CustomFields::useSectionModel(CustomFieldSection::class);
CustomFields::useOptionModel(CustomFieldOption::class);
CustomFields::useValueModel(CustomFieldValue::class);
```
The twin's docblock carries the porting rule: system fields "cannot be deleted by users, only deactivated" (isSystemDefined contract), and every import/executor query pairs `withoutGlobalScopes()` with explicit tenant/entity filters BECAUSE the swapped model now enforces tenant+sort scopes the vendor never did. Schema resources expose per-entity field dictionaries to the assistant ("read crm-schema FIRST to discover valid field codes... Unknown field codes will be rejected" — BaseCreateTool :44).

**Flow:** boot: swap all four vendor models for app twins → every subsequent vendor-repo write now fires app observers/scopes → MCP schema resources publish live field codes/types per entity so AI callers quote real codes → create/update tools validate submitted codes against ValidCustomFields compiled from the same definitions.
**Invariant:** After a model swap, EVERY raw query against vendor tables must consciously choose global-scope bypass + manual tenancy, or inherit tenant filtering silently; the swap must happen before any eager vendor query runs.
**Probe:** `tests/Feature/Mcp/SchemaResourcesTest.php`, `RelaticleServerTest.php`; scope interactions pinned across ImportWizard suites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "useCustomFieldModel CustomField TenantScope SchemaResource", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt vendor-model swapping + published schema dictionaries when you need app-level lifecycle hooks on package-owned tables. Adapt to your framework's model-binding mechanism. Omit the five concrete schema resource bodies. Direct tests cover the resource plane; scope semantics are cross-pinned by executor suites.
