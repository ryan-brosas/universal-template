<!-- capsule-v2 -->
# Partner postback dispatch — how do partners receive server-side event callbacks, and how does the adapter registry keep per-receiver payload shapes out of the dispatcher?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** What is the fan-out contract from a domain event to partner-owned webhook URLs, and which layer signs, transforms, and delivers?

## sendPartnerPostback → PostbackAdapter subclasses → QStash with callback
**Path/Symbol:** `apps/web/lib/postback/send-partner-postback.ts:sendPartnerPostback` (:15-76); abstract base `apps/web/lib/postback/postback-adapters.ts:PostbackAdapter` (:15-71); custom/slack subclasses `postback-adapter-custom.ts`, `postback-adapter-slack.ts`; enrichers `postback-event-enrichers.ts` (:14-84); transformers `postback-event-transformers.ts:PostbackEventTransformers` (:9-41).
**Signature:** `sendPartnerPostback({partnerId, event, data, skipEnrichment?, isTest?})`; triggers = `["lead.created","sale.created","commission.created"]` (`constants.ts:5-9`); delivery payload `{eventId:"evt_"+nanoid(25), event, createdAt, data}`.
**Data Shape:** postback row `{id:"pb_", url (https-only), secret "pbsec_"+16, triggers[], receiver:"custom"|"slack", disabledAt}`; MAX_POSTBACKS=5.

### Decisive source
```ts
const postbacks = await prisma.postback.findMany({ where: {
  partnerId,
  ...(isTest ? {} : { disabledAt: null }),
  triggers: { array_contains: [event] } } });
...
enrichedData = !skipEnrichment && postbackEventEnrichers.has(event)
  ? postbackEventEnrichers.enrich(event, data) : data;
... await Promise.allSettled(adapters.map((adapter) => adapter.execute({...})));
```
(send-partner-postback.ts :24-74)
```ts
const response = await qstash.publishJSON({
  callback: callbackUrl.href, failureCallback: callbackUrl.href,
  url: this.postback.url, body: transformedPayload,
  headers: { "Dub-Signature": signature, "Upstash-Hide-Headers": "true" } });
```
(postback-adapters.ts :47-57)

**Flow:** select the partner's enabled postbacks whose `triggers` array contains the event (Postgres array containment) → enrichment registry converts raw Tinybird snake_case rows into per-event zod-validated payloads (camelCasing keys; click timestamps coerced `new Date(ts + "Z")` to force UTC) — enrichment failures ABORT the whole send (return before any adapter runs); test sends skip enrichment because sample payloads are already enriched → each matched postback gets its adapter by `receiver`: custom adapters re-wrap `{id,event,createdAt,data}`, slack adapters currently throw Not-implemented in every transformer (transformer returning null/throwing silently drops THAT delivery only — execute() is invoked inside the caller's allSettled) → HMAC-SHA256 hex signature over the transformed body (`webhook/signature.ts:2-21`) sent through QStash with success AND failure callbacks pointing back at `/api/postbacks/callback?postbackId&eventId&event`, which base64-decodes QStash's request/response echo and ingests a delivery log row (`response_status: status === -1 ? 503 : status`, `retry_attempt: retried` — callback route :40-52). Secret rotation is a plain update returning the new secret.
**Invariant:** (1) signing happens over the TRANSFORMED body — receivers verify what they actually received, so transform-before-sign ordering is security-critical; (2) `Upstash-Hide-Headers` prevents dub's own auth headers leaking to third parties; (3) delivery outcomes are OBSERVED not enforced — the callback records attempts (including -1 ⇒ 503 for never-delivered) but nothing retries beyond QStash's own policy; (4) one misbehaving receiver cannot block others (allSettled + per-adapter transformer isolation).
**Probe:** deterministic probe: `grep -c 'failureCallback' apps/web/lib/postback/postback-adapters.ts` = 1; `grep -n 'status === -1 ? 503' apps/web/app/api/postbacks/callback/route.ts` = :49. No upstream unit suite covers this plane (recorded caveat).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "sendPartnerPostback", limit: 5 });
```

## Verdict
Adopt the three-layer split (selector → enricher registry → receiver adapters with transform-before-sign via a queue that supports delivery callbacks). Adapt trigger vocabulary and the delivery-log sink. Omit Slack receivers until implemented upstream — porting them today ports throws.
