<!-- capsule-v2 -->
# Team bootstrap listeners — signature-discovered field seeding with a post-create color pass

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** How do you give every new tenant its system-defined custom fields, option colors, and demo data without a migration per tenant — and how do the listeners get registered?

## Tenant bootstrap on TeamCreated
**Path/Symbol:** `app/Listeners/CreateTeamCustomFields.php` (whole, 161L, `final readonly class CreateTeamCustomFields { public function handle(TeamCreated $event): void }`); siblings `app/Listeners/SeedTeamCreditBalanceListener.php` (18L) and `app/Listeners/SwitchTeam.php` (24L, Filament `TenantSet` → `$user->switchTeam($team)`, registered in `app/Providers/Filament/AppPanelProvider.php` :105).
**Signature:** static `MODEL_ENUM_MAP: array<class-string, class-string>` pins Company/Opportunity/Note/People/Task to their field enums; per case, `CustomFieldData(name, code, type, section: HEADLESS 'General', systemDefined, width, settings)` → `CustomsFieldsMigrators->new(model, fieldData)[->options(...)]->create()`.
**Data Shape:** registration asymmetry is the porting-relevant fact: `SeedTeamCreditBalanceListener` is explicitly registered (`app/Providers/AppServiceProvider.php` :139 `Event::listen(TeamCreated::class, SeedTeamCreditBalanceListener::class)`), while `CreateTeamCustomFields` has NO explicit registration anywhere in app/config/bootstrap — it is picked up by Laravel's signature-based event discovery from the typed `handle(TeamCreated $event)`.

### Decisive source
```php
public function handle(TeamCreated $event): void
{
    $team = $event->team;
    $this->migrator->setTenantId($team->id);
    DB::transaction(function (): void {
        foreach (self::MODEL_ENUM_MAP as $modelClass => $enumClass) {
            foreach ($enumClass::cases() as $enum) {
                $this->createCustomField($modelClass, $enum);
            }
        }
    });
    if ($team->isPersonalTeam() && Feature::active(OnboardSeed::class)) {
        $team->loadMissing('owner');
        $fixtureSet = $team->onboarding_use_case instanceof OnboardingUseCase
            ? $team->onboarding_use_case->getFixtureSet()
            : 'sales';
        $this->onboardSeeder->run($owner, $team, $fixtureSet);
    }
}
```
Option colors need a SECOND pass because option ids exist only after create: `applyColorsToOptions()` reads `$customField->options()->withoutGlobalScopes()->get()` (the migrator's tenant scope is not armed mid-bootstrap), filters by name→color map, and writes all settings in ONE hand-built bulk statement — `UPDATE … SET settings = CASE WHEN id = ? THEN ? … END` with a pgsql-only `::json` cast on the CASE expression — instead of N model saves.

**Flow:** Jetstream emits `TeamCreated` → discovery invokes the listener → `setTenantId` arms the migrator → one transaction creates every system field for all five models → if personal team AND `OnboardSeed` Pennant feature active (resolves `(bool) config('relaticle.features.onboard_seed', true)`), seed the fixture set from the team's onboarding use case enum (fallback `'sales'`).
**Invariant:** Field creation is transactional and enum-driven — the enum is the single source of field shape (display name, code, type, width, option settings); colors are a separate idempotent pass keyed by option NAME, never by index. Demo seeding is gated on BOTH personal-team AND feature flag.
**Probe:** `tests/Feature/Onboarding/CreateTeamOnboardingTest.php` (seeds demo data when `Feature::define(OnboardSeed::class, true)`); `tests/Feature/FeatureFlagsTest.php` :14-25 pins Billing off-by-default and that `Feature::flushCache()` is required after config changes. All six `app/Features/*.php` are 13-line config-resolving classes — Pennant as a config-backed switch.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "CreateTeamCustomFields MODEL_ENUM_MAP applyColorsToOptions OnboardSeed TeamCreated", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt enum-driven per-tenant field bootstrap with signature-based listener discovery when your framework supports it (one typed handle method replaces registration boilerplate). Adapt the enum map to your domain models. Keep the post-create second pass for anything needing generated child ids; prefer one bulk CASE update over per-row saves. Omit the Pennant flag indirection if you have no per-deployment feature surface.
