<!-- capsule-v2 -->
# Event-suppressed demo seeding — how do you seed realistic tenant data through models whose observers, sort ordering, and EAV writers you have deliberately switched off?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** When onboarding seeds demo records via Eloquent with `Model::withoutEvents`, what framework behavior did you disable — and what must be reimplemented by hand so the seeded workspace behaves like a real one?

## Registry-linked fixture seeding with manual sort positions and bulk EAV writes
**Path/Symbol:** `packages/OnboardSeed/src/OnboardSeedManager.php` (whole, 68L, `generateFor(Authenticatable $user, ?Team $team = null, string $fixtureSet = 'sales'): bool`); `packages/OnboardSeed/src/Support/BaseModelSeeder.php` (whole, 253L); `packages/OnboardSeed/src/Support/BulkCustomFieldValueWriter.php` (68L); `packages/OnboardSeed/src/Support/FixtureRegistry.php` (static type+key→Model map); `packages/OnboardSeed/src/Support/FixtureLoader.php` (per-set YAML dirs).
**Signature:** five seeders run in dependency order (Company → People → Opportunity → Task → Note) inside `Model::withoutEvents(...)`, each `seed(Team $team, Authenticatable $user)` = `prepareForSeed` (resolve the tenant's custom-field definitions ONCE, keyed by code) → `createEntitiesFromFixtures` → `flushCustomFieldValues()`. Whole run wrapped in try/report/return-false, `FixtureLoader::reset()` in `finally`.
**Data Shape:** fixtures are YAML files under `resources/fixtures/{sales,fundraising,general}/<entities>/*.yaml`; `FixtureRegistry` (static, cleared per run) lets later seeders resolve earlier entities by key (task fixture `assigned_people: [alfred]` → registry lookup). `BulkCustomFieldValueWriter` queues rows (`CustomFieldValue::getValueColumn(type)` picks the value column, `SafeValueConverter::toDbSafe` converts, arrays json_encoded), NULL-defaults all columns, and inserts in 500-row chunks.

### Decisive source
```php
// SortableTrait's creating event is suppressed by withoutEvents(),
// so we manually assign sequential order_column values.
if (in_array(SortableTrait::class, class_uses_recursive($this->modelClass), true)) {
    $this->positionCounter++;
    $attributes['order_column'] = bcmul((string) $this->positionCounter, DecimalPosition::DEFAULT_GAP, DecimalPosition::SCALE);
}
```
```php
// TaskSeeder: the dashboard's "My tasks" panel reads task_user, so seeded
// tasks must be assigned to the new owner. Attaching CRM people alone
// leaves a brand-new workspace showing an empty task list on its very
// first screen.
$task->assignees()->syncWithoutDetaching([$user->getAuthIdentifier()]);
```

**Flow:** team created (bootstrap listeners may gate this on the `OnboardSeed` Pennant flag + personal-team check, see `team-bootstrap-listeners.md`) → `FixtureRegistry::clear()` + fixture set loaded → per entity: fixture YAML → template expressions evaluated (`{{+3d}}`, `{{nextWeek}}` relative to seed time so demo data always looks current) → option labels mapped to ids via the pre-loaded definitions → model `create` with `creation_source: SYSTEM` + manual `order_column` → EAV values queued → 500-chunk flush per entity.
**Invariant:** Everything the suppressed events would have done must be done by hand: SortableTrait's `order_column` (decimal-gap positions via `bcmul`), any observer side effects. Cross-references resolve through the registry, never by re-querying by name. A seeding failure is reported and returns false — never thrown into registration. A new workspace's first screen must not be empty (owner assigned to seeded tasks).
**Probe:** No dedicated Pest suite exists for the package (grep over `tests/` finds none) — behavior is pinned indirectly by `tests/Feature/Notifications/ManageNotificationPreferencesTest.php`-style onboarding flows and the bootstrap-listener tests cited in `team-bootstrap-listeners.md`. Coverage caveat: this capsule's claims rest on direct source reads of all seven package files, not a direct test.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "OnboardSeedManager generateFor BaseModelSeeder registerEntityFromFixture BulkCustomFieldValueWriter flush FixtureRegistry withoutEvents order_column", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern for any demo/fixture seeding over eventful models: enumerate what `withoutEvents` disables (observers, sortable ordering, activity logging) and reimplement each by hand; resolve cross-fixture references through an explicit registry; evaluate relative date templates at seed time; bulk-write EAV values in chunks with explicit column defaults; mark seeded rows with a creation source. Adapt the YAML fixture layout and the seeder sequence to your domain. Companion to `team-bootstrap-listeners.md` (the bootstrap that invokes seeding) and `import-customfield-value-upsert.md` (the production twin of the 500-chunk EAV write discipline).
