<!-- capsule-v2 -->
# Singleton tag-cache settings store — how do you serve and invalidate a one-row global configuration without serving stale or throwing on a missing row?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** How does a single seeded settings row back every page (login included) with caching, and what happens when the row is absent?

## getInstanceSettings + updateTag-on-write around the id:1 row
**Path/Symbol:** `apps/web/src/features/instance-settings/data.ts:getInstanceSettings` (lines 28–66); `apps/web/src/features/instance-settings/mutations.ts:updateInstanceSettings` (lines 9–25) and `updateInstanceFooterLinks` (lines 63–74); tag constant `constants.ts:instanceSettingsTag` (line 3); Prisma model `packages/database/prisma/models/instance-settings.prisma:InstanceSettings`.
**Signature:** `getInstanceSettings() → { instanceId, disableUserRegistration, appName, primaryColor, primaryColorDark, logo, logoDark, logoIcon, hideAttribution, footerLinks }` — every scalar independently null-coalesced.
**Data Shape:** exactly one row, `id: 1`, seeded by migration; there is no create path in the feature — writes are plain `update`s.

### Decisive source
```ts
export const getInstanceSettings = unstable_cache(
  async () => {
    const instanceSettings = await prisma.instanceSettings.findUnique({
      where: { id: 1 },
      select: { instanceId: true, disableUserRegistration: true,
        appName: true, /* …colors/logos… */ footerLinks: true },
    });
    return {
      instanceId: instanceSettings?.instanceId ?? null,
      disableUserRegistration: instanceSettings?.disableUserRegistration ?? false,
      // …each field coalesced individually…
      footerLinks: parseFooterLinks(instanceSettings?.footerLinks),
    };
  },
  [],
  { tags: [instanceSettingsTag] },
);
```
```ts
// The id 1 row is seeded by migration, so it always exists
await prisma.instanceSettings.update({ where: { id: 1 }, data });
updateTag(instanceSettingsTag);
```

**Flow:** any server component (`login`, `verify`, control panel), the branding config resolver (`features/branding/data.ts:getCustomBrandingConfig`, which SKIPS the DB entirely during maintenance mode so that page can render while the DB is unreachable), and the registration gate (`getRegistrationEnabled`: feature flag first, then `!disableUserRegistration`) all read through this one cached function → each mutation writes id:1 then calls `updateTag(instanceSettingsTag)` in the same request, killing the cache entry.
**Invariant:** two failure postures compose here. Missing row ⇒ per-field defaults (`?? null` / `?? false`), never a throw — the login page renders even if the singleton vanished. Staleness ⇒ tag-scoped invalidation: readers never pass TTLs or revalidate flags; writers own freshness by naming the same string constant both sides. The `select` projection doubles as an allowlist — new columns stay private until deliberately exposed.
**Probe:** no dedicated upstream test for data.ts/mutations.ts (caveat recorded). Behavioral anchors verified by direct read: `where: { id: 1 }` appears at data.ts:31–33, mutations.ts:18–20/:35–37/:50–52/:65–67; `updateTag(instanceSettingsTag)` at mutations.ts:24/:58/:73. Consumers confirmed via trace_path inbound (10 callers: login/verify pages, control panel, branding data/loaders, getRegistrationEnabled).

## Get live surrounding code
```ts
// BM25 search_graph totals 0 on this identifier cluster (server flake on
// identifier-style queries, same behavior recorded pass 2); search_code resolves:
await mcp.codebase_memory.search_code({ project: "rallly", pattern: "instanceSettingsTag", limit: 10 });
```

## Verdict
Adopt the seeded-singleton + tagged-cache + defaults-on-missing shape for any per-install config; adapt `unstable_cache`/`updateTag` to your framework's cache-tag API; omit the maintenance-mode bypass only if you have no degraded-mode page. Do not "fix" the plain `update` into an upsert: the migration-seeded row is the invariant that makes write-after-read races impossible to turn into duplicate singletons — enforce seeding instead.
