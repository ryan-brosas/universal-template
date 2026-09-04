<!-- capsule-v2 -->
# Click ingestion with fail-closed dedup — what guards turn a raw redirect hit into exactly one analytics event, and what happens when Redis dies?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** What is the full recordClick pipeline (dedup, bot/QR classification, geo enrichment, fan-out), and why does a cache failure DROP the click?

## recordClick — gate ladder then waitUntil(allSettled) ingest
**Path/Symbol:** `apps/web/lib/tinybird/record-click.ts:recordClick` (22-236); dedup store `apps/web/lib/api/links/record-click-cache.ts` (Redis `irc:` keys); helpers `detectBot/detectQr/getIdentityHash`.
**Signature:** `recordClick({ req: Request, clickId?, linkId, workspaceId?, domain, key, url?, programId?, partnerId?, skipRatelimit?, timestamp?, referrer?, trigger = "link", shouldCacheClickId? }): Promise<clickData | null>`.
**Data Shape:** flat click row (~30 columns): `timestamp, identity_hash, click_id, workspace_id ("" fallback), link_id, domain, key, url ("")`, geo block (`ip ""` for EU or invalid, continent/country/region/city/lat/long "Unknown" defaults, vercel_region ""), UA block (device/vendor/model/browser/engine/os/cpu, `bot` flag), `qr`, `referer "(direct)"` domain + full url, `trigger` (link|qr|deeplink).

### Decisive source
```ts
if (!clickId) return null;                                   // no attribution id ⇒ not a trackable click
if (req.headers.has("dub-no-track") || searchParams.has("dub-no-track")) return null; // opt-out
if (trigger !== "deeplink") { if (detectBot(req)) return null; }  // bots never counted
const identityHash = await getIdentityHash(req);
if (!skipRatelimit) {
  try {
    const cachedClickId = await recordClickCache.get({ domain, key, identityHash });
    if (cachedClickId) return null;                          // same person+link within 1h ⇒ dedup
  } catch (error) {
    console.error(`[recordClickCache error]: ${error}`);
    return null;  // FAIL-CLOSED: redis down ⇒ drop the click rather than flood TB/MySQL
  }
}
const isQr = detectQr(req); if (isQr) trigger = "qr";
// region: geolocation().region is the VERCEL EDGE region, not the user's — use the header instead
const { continent, region } = VERCEL ? {
  continent: req.headers.get("x-vercel-ip-continent"),
  region: req.headers.get("x-vercel-ip-country-region"),
} : LOCALHOST_GEO_DATA;

if (shouldCacheClickId)
  await redis.set(`clickIdCache:${clickId}`, clickData, { ex: 60 * 5 }); // TB ingest lag bridge

waitUntil((async () => {
  const response = await Promise.allSettled([
    fetchWithRetry(`${TINYBIRD_API_URL}/v0/events?name=dub_click_events&wait=true`,
      { method: "POST", headers: { Authorization: `Bearer ${TINYBIRD_API_KEY}` }, body: JSON.stringify(clickData) }),
    recordClickCache.set({ domain, key, identityHash, clickId }),   // arm the 1h dedup window AFTER recording
    publishLinkClickEvent({ linkId, timestamp: clickData.timestamp, ... }),
    publishWorkspaceClickEvent(clickData),
  ]);
  // rejected rows logged per-operation with named operation labels — never rethrown
})());
return clickData;   // returned synchronously for the redirect response, side effects are async
```

**Flow:** presence gates (clickId → no-track opt-out → bot → dedup-cache hit) each return null early; survivors build an enriched row from Vercel edge headers (`x-vercel-ip-*`) with localhost fallbacks outside Vercel; optional pre-ingest Redis mirror of the click row (5-min TTL) covers Tinybird's indexing delay; async fan-out records to TB, arms the dedup key, publishes two realtime streams; every rejection is logged by operation name.
**Invariant:** Dedup is FAIL-CLOSED BY DESIGN — availability of downstream stores outranks completeness, so a dead Redis silently discards clicks instead of letting them through un-deduplicated. The dedup key arms only AFTER successful scheduling of the record (set is inside the allSettled): a crash between get-miss and set means the next identical click records twice — accepted over the reverse. EU visitors' IPs are never persisted (GDPR) but their clicks still count. The clickIdCache mirror exists because Tinybird events are not immediately queryable; consumers needing instant reads read Redis first. `trigger="deeplink"` skips bot checks because app-store handoffs look like bots.
**Probe:** no direct unit test for the full pipeline (coverage caveat — detectBot/detectQr have their own suites in middleware tests). Deterministic probe: missing `clickId` ⇒ null before ANY I/O; `dub-no-track` header short-circuits even with valid clickId; mocked `recordClickCache.get` throw ⇒ null and NO fetch issued.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "recordClick clickIdCache dub_click_events", limit: 5 });
// → tinybird.record-click.recordClick @ record-click.ts 22-236
```

## Verdict
Adopt the ordered presence-gate ladder, post-record arming of the dedup window, fail-closed cache semantics, privacy-scoped field drops, and the pre-query Redis mirror over an eventually-consistent warehouse. Adapt the dedup window (1h), the identity primitive, and the geo header names. Omit QR/deeplink triggers if you have neither.
