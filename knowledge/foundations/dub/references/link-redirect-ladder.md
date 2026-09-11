<!-- capsule-v2 -->
# Link redirect decision ladder — in what ORDER must a short-link edge evaluate password/expiry/disabled/geo/device/deeplink branches, and which are rewrites vs redirects?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** A link can carry destination URL, password, expiry+expiredUrl, disabled flag, geo/device overrides, cloaking, A/B variants and app-store deep links — what is the authoritative branch order and response type of each?

## LinkMiddleware — 610-line edge orchestrator
**Path/Symbol:** `apps/web/lib/middleware/link.ts:LinkMiddleware` (40-610); root dispatcher `apps/web/middleware.ts:middleware` (35-90).
**Signature:** `LinkMiddleware(req: NextRequest, ev: NextFetchEvent): Promise<NextResponse>`.
**Data Shape:** consumes the Redis-cached link (`linkCache.get` → `formatRedisLink` fallback `getLinkViaEdge`): `{id, url, password, proxy, rewrite, expiresAt, disabledAt, ios, android, geo, expiredUrl, doIndex, testVariants, testCompletedAt, projectId, programId?, partnerId?}`.

### Decisive source (branch order is the contract)
```ts
// middleware.ts — host-based router BEFORE any link logic
if (APP_HOSTNAMES.has(domain)) return AppMiddleware(req);      // app
if (API_HOSTNAMES.has(domain)) return ApiMiddleware(req);      // api
if (path.startsWith("/stats/")) return /* rewrite to stats */; // stats pages
// ... .well-known / DEFAULT_REDIRECTS / admin / partners ...
if (isValidUrl(fullKey)) return CreateLinkMiddleware(req);     // POST-via-GET hack
return LinkMiddleware(req, ev);

// link.ts — inside LinkMiddleware, strict order:
// 1 inspect mode (`key+`, only when !password)  → REWRITE /inspect
// 2 password (no/bad pw)                        → REWRITE /password/[id]
// 3 banned workspace                            → REWRITE /[domain]/banned
// 4 disabledAt                                  → REWRITE /[domain]/notfound
// 5 expired (+expiredUrl ? REDIRECT : REWRITE expired page)
// 6 no url (root placeholder)                   → track + REWRITE /${domain}
// 7 bot && proxy                                → REWRITE proxy page
// 8 custom URI scheme                           → REWRITE interstitial
// 9 rewrite (cloak)                             → REWRITE /cloaked/<url>
// 10 ios + iOS UA   → app-store URL? deeplink splash REDIRECT : REDIRECT ios
// 11 android + Android UA → play-store? deeplink splash : REDIRECT android
// 12 geo[country] match                          → REDIRECT geo target
// 13 else regular                                → REDIRECT url
```
Every redirect branch ends `status: key === "_root" ? 301 : 302`.

**Flow:** parse host/key → normalize → cache lookup (miss: DB fetch + `ev.waitUntil` async cache fill, partner enrichment included) → ladder above. Click recording (`recordClick` via Tinybird) is fired with `ev.waitUntil` on EVERY tracking branch (7-13) but never on rewrites 1-5 — password/expired/disabled clicks are untracked by design.
**Invariant:** order matters — inspect beats password; banned/disabled/expired beat ALL redirects (a banned link must not redirect even if it has device overrides). Rewrites keep the short domain in the address bar (proxy/cloak/password/inspect); redirects leave it. `_root` keys get permanent 301s, everything else 302. Cache-fill after DB miss must be `waitUntil`'d, never awaited into the response path.
**Probe:** no upstream unit test for the full ladder (coverage caveat; consumer-grounded via `tests/utils/http.ts` helpers). Deterministic probe: table-driven assertions that each link fixture produces the expected response type + status code in ladder order.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "LinkMiddleware redirect rewrite expired password geo", limit: 10 });
```

## Verdict
Adopt the ladder as a state machine table: explicit ordered guards, response-type per guard, waitUntil'd side effects only past the gate that earns tracking. Adapt branch set (drop deeplink/appstore if you don't do mobile), status-code policy, and cache transport. Omit partner-link enrichment and Bitly crawl fallback unless porting those features too.
