<!-- capsule-v2 -->
# Top-breakdown hydration — warehouse rows to API objects without leaking dead ids

**Source:** dub AGPL-3.0-or-later `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** After Tinybird returns grouped rows keyed by opaque ids, how does the API enrich them without ever exposing a stale or foreign id?

## Per-groupBy Prisma hydration with drop-on-miss
**Path/Symbol:** `apps/web/lib/analytics/get-analytics.ts` :207-400 (top_links exemplar :207-251; partner/tag/folder/partnerTag/group variants :252-389; non-top fallback :392-400).
**Signature:** internal branches of `getAnalytics`; each ends in `analyticsResponse[groupBy].parse(...)`.
**Data Shape:** warehouse rows: `{ groupByField, clicks?, leads?, sales?, saleAmount?, country?, region? }` → hydrated DTOs with rebuilt link shapes (`shortLink`, punycode key) or nested entities.

### Decisive source
```ts
const links = await prisma.link.findMany({
  where: { id: { in: response.data.map((item) => item.groupByField) } },
  select: { id: true, domain: true, key: true, url: true, ... },
});

return response.data
  .map((item) => {
    const link = links.find((l) => l.id === item.groupByField);
    if (!link) {
      return null;
    }

    link.key = decodeKeyIfCaseSensitive({ domain: link.domain, key: link.key });

    return analyticsResponse[groupBy].parse({
      ...link,
      link: link.id,
      key: punyEncode(link.key),
      shortLink: linkConstructor({ domain: link.domain, key: punyEncode(link.key) }),
      createdAt: link.createdAt.toISOString(),
      ...item,
    });
  })
  .filter((d) => d !== null);
```
(get-analytics.ts :208-251 condensed)

```ts
return response.data.map((item) =>
  schema.parse({
    ...item,
    [SINGULAR_ANALYTICS_ENDPOINTS[groupBy!]]: item.groupByField,
  }),
);
```
(get-analytics.ts :395-400)

**Flow:** ONE batched `findMany({id in})` per entity type → JS-side find join → missing id ⇒ null ⇒ dropped (six identical drop-guards in the file) → case-sensitive-domain keys decoded then re-encoded (punycode) into a rebuilt `shortLink` → strict zod whitelist parses the merged object → non-top endpoints rename `groupByField` to the endpoint's singular key (`SINGULAR_ANALYTICS_ENDPOINTS`, constants.ts :94-121).
**Invariant:** hydration is a FILTER, not an error — warehouse rows pointing at deleted/foreign MySQL rows vanish silently (drift tolerance), and the strict schemas guarantee warehouse columns can't leak into API responses.

**Probe:** executed: `grep -n 'prisma.link.findMany' ...` → :208; `grep -c 'filter((d) => d !== null)' ...` → 6; `grep -n 'punyEncode(link.key)' ...` → :242; `grep -n 'SINGULAR_ANALYTICS_ENDPOINTS\\[groupBy!\\]' ...` → :398. Test anchors: `tests/analytics/get-analytics.test.ts` validates EVERY VALID_ANALYTICS_ENDPOINTS groupBy against strict response schemas (:31-39, CI-gated integration, offline-blocked).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", name_pattern: "^getAnalytics$", limit: 5 });
```
(also live: `SINGULAR_ANALYTICS_ENDPOINTS` in apps/web/lib/analytics/constants.ts :94-121.)

## Verdict
Adopt batched-id hydration with drop-on-miss and strict re-whitelisting. Adapt entity types and key codecs. Omit the punycode step if your keyspace is ASCII-only (keep decode-if-case-sensitive though).
