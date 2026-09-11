<!-- capsule-v2 -->
# Pennant feature flags — config-resolving feature classes as a per-deployment switch plane

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5`; direct source+test read (Codebase Memory MCP not connected this session). **Question:** When a feature-flag system is overkill for config-only flags, what is the minimal shape that keeps call sites flag-shaped and test-friendly?

## Six 13-line classes, one resolve contract
**Path/Symbol:** `app/Features/{Billing,Blog,Documentation,OnboardSeed,SocialAuth,SupportMenu}.php` (each 13L, `final readonly class X { public function resolve(): bool { return (bool) config('relaticle.features.<snake_name>', <default>); } }`); consumers e.g. `app/Listeners/CreateTeamCustomFields.php` (`Feature::active(OnboardSeed::class)`).
**Signature:** no storage, no scopes, no per-user resolution — `resolve()` reads one config key with a baked-in default (`onboard_seed` defaults true; `billing` defaults false; the rest false).
**Data Shape:** config tree `relaticle.features.*`; Pennant caches resolved values, so tests must call `Feature::flushCache()` after `config()->set(...)`.

### Decisive source
```php
final readonly class Billing
{
    public function resolve(): bool
    {
        return (bool) config('relaticle.features.billing', false);
    }
}
```
The only behavioral consumer mined this pass is the team-bootstrap listener: demo seeding runs only when `$team->isPersonalTeam() && Feature::active(OnboardSeed::class)` — the flag is the deployment-level kill switch for fixture data, layered on top of a structural condition.

**Flow:** call site asks `Feature::active(SomeFeature::class)` → Pennant invokes `resolve()` → config value (cached) → boolean. Deployment toggles the flag by config, not by database or code change.
**Invariant:** Flags stay CLASSES so call sites are statically discoverable (grep/PHPStan) and type-safe — no stringly-typed flag names. Defaults live in the class, making the off-state visible at the definition site. The flag plane carries no per-tenant logic; tenant-level conditions (like personal-team) belong at the call site.
**Probe:** `tests/Feature/FeatureFlagsTest.php` — per-flag `describe` blocks pin off-by-default (Billing) and config activation with `Feature::flushCache()` between set and assert; OnboardSeed case proves the flag actually gates demo seeding end-to-end.

## Get live surrounding code
**Retrieve:** (canonical graph form; executed this session as exact-symbol grep fallback — hit confirmed)
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "Features Billing OnboardSeed resolve Feature::active relaticle.features", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt this shape when you want flag-shaped call sites without a flag database: one class per flag, config-only `resolve()`, defaults in the class. Adapt the config tree name. Keep `flushCache()` discipline in tests — Pennant memoization is the one trap. Omit entirely (plain `config()` calls) if you never expect to swap resolution to per-user or per-team storage; the value of the class indirection is exactly that future swap.
