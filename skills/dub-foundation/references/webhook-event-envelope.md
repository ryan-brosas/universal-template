<!-- capsule-v2 -->
# Webhook event envelope — what exact JSON shape and event-ID scheme do subscribers receive, and how is the per-trigger data validated?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** What is the stable public contract of a webhook body (envelope, id prefix, trigger taxonomy) and how are the nine payload families kept schema-valid before enqueue?

## webhookPayloadSchema + prepareWebhookPayload + trigger constants
**Path/Symbol:** `apps/web/lib/webhook/schemas.ts:webhookPayloadSchema` (62-72) + `clickWebhookEventSchema` (45-48) + `metadataSchema`/`coerceJsonString` (37-51); `apps/web/lib/webhook/transform.ts:prepareWebhookPayload` (123-130); `apps/web/lib/webhook/constants.ts:WEBHOOK_TRIGGERS` (31-34) + prefixes (5-9).
**Signature:** `prepareWebhookPayload(trigger: WebhookTrigger, data: any): z.infer<typeof webhookPayloadSchema>`.
**Data Shape:** envelope `{id: "evt_<nanoid 25>", event: <one of 12 triggers>, createdAt: ISO string, data: any}`. Trigger taxonomy is two-tier: WORKSPACE_LEVEL (`link.created|updated|deleted|clicked`, `lead.created`, `sale.created`) + PROGRAM_LEVEL (`partner.application_submitted|enrolled`, `commission.created`, `bounty.created|updated`, `payout.confirmed`). ID prefixes: `wh_` (webhook), `whsec_` (secret), `evt_` (event).

### Decisive source
```ts
// transform.ts — the ONLY place an event id is born
export const prepareWebhookPayload = (trigger: WebhookTrigger, data: any) => {
  return webhookPayloadSchema.parse({
    id: `${WEBHOOK_EVENT_ID_PREFIX}${nanoid(25)}`,
    data: data,
    event: trigger,
    createdAt: new Date().toISOString(),
  });
};
```
```ts
// schemas.ts — lenient-by-design metadata coercion
const coerceJsonString = (val: unknown) => {
  if (typeof val === "string") {
    try { return JSON.parse(val); } catch { return val; }
  }
  return val;
};
const metadataSchema = z.preprocess(coerceJsonString,
  z.record(z.string(), z.any()).nullish().default(null));
```

**Flow:** event emitters call `sendWorkspaceWebhook({trigger, ...})` → `prepareWebhookPayload` parses the envelope through `webhookPayloadSchema` (throws on invalid trigger, guarantees `evt_` id + ISO createdAt) → per-family schemas (`lead/sale/click`) validate `data` upstream in Tinybird→webhook transforms; the integration test re-parses delivered bodies against a trigger→schema table.
**Invariant:** the envelope is parsed (not just typed) at creation — an invalid trigger name can never be enqueued. `data` inside the envelope is intentionally `z.any()`; strictness lives in the family schemas, keeping the envelope version-stable while payloads evolve. `metadata` is forgiving by contract: JSON-string-encoded or object both parse to object-or-null. The `evt_` prefix doubles as the callback correlation key.
**Probe:** `tests/webhooks/index.test.ts` — `test.each(WEBHOOK_TRIGGERS)` runs all 12 triggers; line 145 asserts delivered `eventId?.startsWith("evt_")`; lines 155-157 assert `receivedBody.event === trigger`, `receivedBody.data` deep-equals input, and `eventSchemas[trigger].safeParse(...).success`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "webhookPayloadSchema prepareWebhookPayload WEBHOOK_TRIGGERS", limit: 10 });
```

## Verdict
Adopt the envelope discipline: prefixed event IDs minted in exactly one function, parse-at-creation with enum'd triggers, `any`-typed data slot guarded by per-family schemas at the edges, tolerant metadata coercion. Adapt the trigger list and family schemas to your domain. Omit the OpenAPI `.meta()` spec duplication unless you publish SDKs.
