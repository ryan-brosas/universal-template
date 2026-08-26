<!-- capsule-v2 -->
# Webhook receiver dialects — how do you adapt one event payload for integration platforms (Slack/Segment/Zapier) that each expect a different shape?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** When subscribers include third-party platforms with fixed ingestion formats, where do classification, per-receiver transformation, and transport quirks live?

## classify → transform → per-receiver headers
**Path/Symbol:** `apps/web/lib/webhook/utils.ts:identifyWebhookReceiver` (23-27) + `webhookReceivers` map (5-11); `apps/web/lib/webhook/qstash.ts:transformPayload` (132-147) + publish headers (95-111); `apps/web/lib/integrations/slack/transform.ts:formatEventForSlack`, `apps/web/lib/integrations/segment/transform.ts:formatEventForSegment`.
**Signature:** `identifyWebhookReceiver(url: string): WebhookReceiver` (Prisma enum: `user | zapier | make | slack | segment`); `transformPayload({payload, receiver})` is module-private.
**Data Shape:** classification table is hostname-keyed: `{"zapier.com":"zapier","hooks.zapier.com":"zapier","make.com":"make","hooks.slack.com":"slack","api.segment.io":"segment"}`; default `"user"`.

### Decisive source
```ts
// utils.ts — exact-hostname lookup, no substring matching
const webhookReceivers: Record<string, WebhookReceiver> = {
  "zapier.com": "zapier",
  "hooks.zapier.com": "zapier",
  "make.com": "make",
  "hooks.slack.com": "slack",
  "api.segment.io": "segment",
};
export const identifyWebhookReceiver = (url: string): WebhookReceiver => {
  const { hostname } = new URL(url);
  return webhookReceivers[hostname] || "user";
};
```
```ts
// qstash.ts — dialect transform + platform auth header at the TRANSPORT layer
const response = await qstash.publishJSON({
  url: webhook.url,
  body: finalPayload,                       // already transformed
  headers: {
    "Dub-Signature": signature,
    "Upstash-Hide-Headers": "true",
    ...(receiver === "segment" && {         // Segment needs server-side auth
      "Upstash-Forward-Authorization": createSegmentBasicAuthHeader(webhook.secret),
    }),
  },
  callback: callbackUrl.href,
  failureCallback: failureCallbackUrl.href,
});
```

**Flow:** enqueue time only (never delivery time): classify by exact hostname → switch on receiver to swap the body (`formatEventForSlack` / `formatEventForSegment` / passthrough) → sign the TRANSFORMED body → attach receiver-specific transport headers → publish.
**Invariant:** classification is exact-hostname equality, not suffix/substring match (`evil-zapier.com` must NOT classify as zapier). The HMAC signature is computed AFTER transformation — receivers verify what they actually receive. Receiver-specific credentials reuse the same `webhook.secret` column (one secret per endpoint, dual-purposed). Unknown hosts are first-class `"user"` receivers, never rejected.
**Probe:** no upstream unit test isolates `identifyWebhookReceiver`; it is exercised transitively by every `tests/webhooks/index.test.ts` case via `sendWebhooks`. Deterministic probe: assert the map lookup returns `user` for unlisted hostnames and exact matches otherwise. Coverage caveat recorded.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "identifyWebhookReceiver formatEventForSlack formatEventForSegment transformPayload", limit: 10 });
```

## Verdict
Adopt: hostname-exact receiver classification, transform-before-sign ordering, transport-header injection for platforms needing server-side auth, enum-with-default classification. Adapt the receiver set and dialect formatters to your integrations. Omit dub's Slack Block Kit / Segment spec bodies unless you target those platforms.
