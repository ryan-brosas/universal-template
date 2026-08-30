<!-- capsule-v2 -->
# System-field enums — compile-time field vocabularies per entity

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How do you give system-defined (non-user-created) fields a typed, seeded, self-describing configuration?

## CustomFieldTrait + per-entity enums
**Path/Symbol:** `app/Enums/CustomFields/CustomFieldTrait.php` (whole, 170L); consumers: `app/Enums/CustomFields/{CompanyField,PeopleField,OpportunityField,TaskField,NoteField}.php`; type vocabulary mirror `app/Enums/CustomFieldType.php` (35L).
**Signature:** trait methods: `getDisplayName()`, abstract `getFieldType(): string`, `isSystemDefined()` (=true), `isListToggleableHidden()`, `getWidth()`, `getOptions(): ?array`, `getDescription()`, `getOptionColors()`, `hasColorOptions()`, `allowsMultipleValues()`, `getMaxValues()` (5 if multi), `isUniquePerEntityType()`, aggregate `getConfiguration(): array`.
**Data Shape:** Each entity enum case = one system field; config assembled into the exact array shape consumed by seeding (`CreateTeamCustomFields` listener seeds them per new team).

### Decisive source
```php
/**
 * Get whether this field is system defined
 *
 * System-defined fields cannot be deleted by users, only deactivated.
 */
public function isSystemDefined(): bool { return true; }

public function getMaxValues(): int { return $this->allowsMultipleValues() ? 5 : 1; }
```
Defaults-with-override design: optional capabilities (options, colors, description) default null/false and are overridden only by cases that need them — so a new system field is ONE enum case, never a migration. The app-level `CustomFieldType` enum deliberately mirrors the vendor package's string values ("Maps to the field types available in the relaticle/custom-fields package") for type-safe references.

**Flow:** team creation listener iterates each entity enum → `getConfiguration()` feeds definition creation (name/type/systemDefined/width/options/…) → UI reads the same enums for fixed column sets and filter presets → MCP schema resources reference enum values (e.g. `OpportunityField::STAGE->value`) instead of raw strings.
**Invariant:** System fields must seed as `system_defined=true` (deactivate-only); the local enum's string values must stay byte-identical to the vendor package's keys or definitions silently mis-type.
**Probe:** `app/Listeners/CreateTeamCustomFields.php::createCustomField` (:78-113) exercised via team-registration tests; no dedicated enum unit file (caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CustomFieldTrait getConfiguration CompanyField CreateTeamCustomFields", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt enum-as-config for built-in field vocabularies with a defaults-carrying trait. Adapt the vendor-mirror discipline to your own extension points. Omit the concrete CRM fields. Caveat: covered indirectly via listener/team tests.
