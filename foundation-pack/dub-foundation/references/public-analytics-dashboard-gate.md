<!-- capsule-v2 -->
# Public analytics dashboard gate — how do you serve link/folder analytics with NO authenticated user?

**Source:** dub AGPL-3.0 `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** What replaces session authz when analytics must be publicly reachable at /api/analytics/dashboard?

## Opt-in boolean flag as the only access control
**Path/Symbol:** `apps/web/app/api/analytics/dashboard/route.ts:GET` (:16-:187).
**Signature:** `export const GET = async (req: Request)` — note the ABSENCE of any `withWorkspace`/`withPartnerProfile` wrapper.
**Data Shape:** query needs `domain+key` (link) OR `folderId`; each candidate row carries a `dashboard: boolean` column; workspace context is joined through the row (`project: {id, plan, usage, usageLimit, createdAt}`).

### Decisive source
```ts
if (!folder?.dashboard) {
  throw new DubApiError({
    code: "forbidden",
    message: "This folder does not have a public analytics dashboard",
  });
}
```
(the link twin at :122 reads "This link does not have…")

**Flow:** parse → require domain+key or folderId → folder branch: `prisma.folder.findUnique` including its project; link branch: check `DUB_DEMO_LINKS` FIRST (:88) and synthesize `{id, projectId: DUB_WORKSPACE_ID}` without a DB hit, else `prisma.link.findUnique` by `domain_key` → **forbid unless the row's `dashboard` flag is true** → plan-scoped `assertValidDateRangeForPlan` + `usage > usageLimit` gate still apply to anonymous visitors.
**Invariant:** publicity is opt-in PER ROW via a stored boolean; there is no token, no signed URL — turning the flag off revokes access on the next request. Demo links are hard-coded so marketing demos work before any workspace sync. Anonymous traffic is subject to the same plan limits as dashboard users (date range + over-usage forbidden).
**Probe:** direct test exists but is CI-gated: `apps/web/tests/analytics/public-analytics-dashboard.test.ts:8-32` (`describe.runIf(env.CI)`, asserts 200 + strict `analyticsResponse.top_links` parse + every row's `folderId === E2E_PUBLIC_ANALYTICS_FOLDER_ID`). Source anchors observed live: forbidden messages :79/:122, `DUB_DEMO_LINKS.find` :88.

## 60-second whole-query cache
**Path/Symbol:** same file :151-:181.
### Decisive source
```ts
const cacheKey = `analyticsDashboardCache:${JSON.stringify(parsedParams)}`;
const cached = await redis.get(cacheKey);
if (cached) return NextResponse.json(cached);
...
waitUntil(redis.set(cacheKey, response, { ex: 60 }));
```

**Flow:** cache key is the FULL parsed param object serialized — any filter change misses — cached value is the final response body returned verbatim; write is fire-and-forget under waitUntil.
**Invariant:** because the route is public, this cache doubles as abuse protection: repeated scrapers hit Redis, not Tinybird. TTL 60s caps staleness; no invalidation hook (acceptable for public aggregate views).
**Probe:** anchors observed live: `analyticsDashboardCache:` :151, `ex: 60` :181.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "analytics dashboard route", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "dub", qualified_name: "dub.apps.web.app.api.analytics.dashboard.route.GET" });
```

## Verdict
Adopt: per-row opt-in boolean as complete public authz, demo-entity short-circuit, plan gates applied to anonymous callers, full-param Redis cache with short TTL and waitUntil write. Adapt flag location (column vs settings table) and TTL; omit dub's specific DUB_DEMO_LINKS constants. Coverage caveat: direct test is CI-gated integration only; deterministic anchors above substitute locally.
