<!-- capsule-v2 -->
# Event feed funnel — row-level events with dual hydration maps and a drop-vs-placeholder asymmetry

**Source:** dub AGPL-3.0-or-later main@29df217a29631ced4041882a28d2327cc4546f27; Codebase Memory dub. **Question:** How does dub serve /api/events (paginated raw event rows) without leaking stale link ids or losing money rows whose customer row was deleted?

## One pipe, per-type data schema, then two Prisma hydration maps
**Path/Symbol:** apps/web/lib/analytics/get-events.ts:getEvents (:35-259); helpers getLinksMap (:261-277), getCustomersMap (:279-307).
**Signature:** getEvents(params: EventsFilters) -> Promise<(ClickEventResponse|LeadEventResponse|SaleEventResponse)[]>.
**Data Shape:** EventsFilters adds page/limit/includeMetadata/query on top of analytics filters; Tinybird v4_events rows carry click_id/customer_id/link_id/event/metadata(string); output rows are per-event response whitelists.

### Decisive source
```ts
// data schema chosen by eventType map, defaulting to clicks
const pipe = tb.buildPipe({
  pipe: "v4_events",
  parameters: eventsFilterTB,
  data: { clicks: clickEventSchemaTBEndpoint, leads: leadEventSchemaTBEndpoint, sales: saleEventSchemaTBEndpoint }[eventType] ?? clickEventSchemaTBEndpoint,
});
// ...
const [linksMap, customersMap] = await Promise.all([
  getLinksMap(response.data.map((d) => d.link_id)),
  getCustomersMap(rows.map((d) => (d.event === "lead" || d.event === "sale") ? d.customer_id : null).filter(Boolean)),
]);

let link = linksMap[evt.link_id];
if (!link) { return null; }                    // missing link DROPS the event
link = decodeLinkIfCaseSensitive(link);
const transformedLink = transformLink(link, { skipDecodeKey: true });
...
customer: customersMap[evt.customer_id] ?? {   // missing customer gets a PLACEHOLDER
  id: evt.customer_id, name: "Deleted Customer", email: "deleted@customer.com",
  externalId: evt.customer_id, createdAt: new Date("1970-01-01"),
},
```
(get-events.ts :77-86 condensed, :170-182, :186-231 condensed)

**Flow:** window via getStartEndDates -> prepareFiltersForPipe folds legacy qr/region -> ONE v4_events call with eventsFilterTB params (offset=(page-1)*limit, sortBy timestamp, desc default; legacy order!=desc overwrites sortOrder :73-75) -> metadataQueryParser(query) merged ahead of buildAdvancedFilters into the single JSON filters param -> Promise.all hydration maps -> per-row repair (MySQL domain/key win over warehouse :203-205, timestamp + Z UTC coercion :207, region/referer *_processed fallbacks :212-213, non-array testVariants -> null :194-199) -> lead/sale rows add eventId/eventName/metadata(gated by includeMetadata)/customer/nested sale{amount,invoiceId,paymentProcessor,currency} -> per evt.event one of three response schemas .parse -> .filter(non-null).
**Invariant:** links are a FILTER (dead id means the row silently vanishes — same drift tolerance as analytics-top-hydration) but customers are TOTAL (placeholder keeps lead/sale rows auditable — revenue never disappears because a customer row was deleted). The two maps must not be merged: their miss semantics differ deliberately.
**Probe:** executed at pin: grep -n "v4_events" -> :78; grep -n "Deleted Customer" -> :227; grep -n "skipDecodeKey: true" -> :193; grep -n "region_processed" -> :212. Direct test tests/analytics/get-events.test.ts pins strict array parses for all three event kinds (:40/:56/:72) plus advanced-filter country assertions (:79-120); describe.runIf(env.CI) integration-gated (:23) — offline-blocked in this checkout (no node_modules).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getEvents event feed", file_pattern: "get-events", limit: 10 });
// rank-1 observed: dub.apps.web.lib.analytics.get-events.getEvents Function get-events.ts 35-259
```
(also live: trace_path inbound getEvents -> 8 API routes incl. app/(ee)/api/events, events/export, admin/events, embed referrals events, partner-profile program events(+export), cron export fetch-events-batch, beehiiv update-sale-events script.)

## Verdict
Adopt the single-pipe + per-type endpoint schema map, offset pagination, dual hydration maps with drop-link/placeholder-customer semantics, and MySQL-wins domain/key repair. Adapt entity types and placeholder text to your domain. Omit punycode/case-sensitive key handling if your keyspace is ASCII-only.