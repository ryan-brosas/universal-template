<!-- capsule-v2 -->
# Click-ID attribution continuity — how does a click ID survive across middleware → destination → conversion endpoints, and when is it reused vs regenerated?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** How do you thread a click identifier through a stateless edge redirect so later lead/sale endpoints can attribute conversions, including repeat clicks from the same visitor?

## dub_id cookie + recordClickCache + identityHash
**Path/Symbol:** cookie minting `apps/web/lib/middleware/link.ts:257-282` + `apps/web/lib/middleware/utils/create-response-with-cookies.ts` (3-34); reuse source `apps/web/lib/api/links/record-click-cache.ts:RecordClickCache` (12-39); identity `apps/web/lib/middleware/utils/get-identity-hash.ts:getIdentityHash` (8-12); deep-link variant `apps/web/lib/middleware/utils/cache-deeplink-click-data.ts:cacheDeepLinkClickData` (49-78).
**Signature:** `createResponseWithCookies(response, {path, dubIdCookieName, dubIdCookieValue, dubTestUrlValue?})`; `RecordClickCache.get/set({domain, key, identityHash}, clickId?)`.
**Data Shape:** cookie name `dub_id_${domain}_${key}`, value nanoid(16), path-scoped to `/${encodeURI(originalKey)`, maxAge 3600. Redis key `recordClick:${domain}:${key}:${identityHash}` TTL 1h. DeepLink key `deepLinkClickCache:${ip}:${domain}:${key}` TTL 1h, value `{clickId, link:{id,domain,key,url}}`.

### Decisive source
```ts
// link.ts — three-tier clickId resolution
const dubIdCookieName = `dub_id_${domain}_${key}`;
const cookieStore = await cookies();
let clickId = cookieStore.get(dubIdCookieName)?.value;      // 1. browser cookie
if (!clickId) {
  if (shouldCacheClickId) {                                  // 2. Redis by identity
    const identityHash = await getIdentityHash(req);         //    sha256(ip + "-" + ua)
    clickId = (await recordClickCache
      .get({ domain, key, identityHash })
      .catch(() => undefined)) || undefined;
  }
  if (!clickId) clickId = nanoid(16);                        // 3. fresh id
}
```
```ts
// create-response-with-cookies.ts — side-channel on EVERY redirect/rewrite response
response.cookies.set(dubIdCookieName, dubIdCookieValue, { path, maxAge: 60 * 60 });
if (dubTestUrlValue) {
  response.cookies.set("dub_test_url", dubTestUrlValue,
    { path, maxAge: 60 * 60 * 24 * 7 });                     // A/B stickiness = 1 week
}
```

**Flow:** request without cookie → resolve-or-mint clickId → every outgoing response (redirect OR rewrite) carries the cookie via `createResponseWithCookies` → when the link needs conversion attribution (`trackConversion || isPartnerLink || Singular/AppsFlyer URL`), `recordClick` persists the mapping into Redis keyed by identity hash → `/track/lead` + `/track/sale` later read the same cookie to attribute.
**Invariant:** the SAME clickId must reach both the analytics event and the response cookies — regenerate only when neither cookie nor Redis has it. Cookie path is the ORIGINAL (pre-punycode, pre-lowercase) key so it survives case-sensitive domains; the Redis lookup key uses the normalized key. Identity hashing fails soft (`.catch(() => undefined)` → new id) — dedup loss beats request failure. `shouldCacheClickId` gates Redis writes: plain links don't pay the storage cost. A/B sticky cookie lives 1 week vs click-id's 1 hour — different lifetimes are deliberate.
**Probe:** no upstream unit test for the resolution tiers (coverage caveat). Deterministic probe: two requests with identical IP+UA within an hour must produce the same clickId when `shouldCacheClickId` holds; different UA must not.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "createResponseWithCookies recordClickCache getIdentityHash cacheDeepLinkClickData", limit: 10 });
```

## Verdict
Adopt the three-tier resolution (cookie → shared cache by identity hash → mint), the always-attach-cookie discipline on every terminal response, fail-soft dedup lookups, and lifetime separation between click-dedup (1h) and experiment-stickiness (1w). Adapt cookie names/TTLs and the shouldCache predicate to your conversion surface. Omit the deep-link interstitial cache unless you do deferred deep linking.
