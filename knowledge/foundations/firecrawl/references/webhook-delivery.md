<!-- capsule-v2 -->
# Webhook delivery — how do crawl/scrape events reach customer endpoints securely, and what happens on the slow path?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I deliver signed webhooks with SSRF protection, event filtering, and a queue-vs-inline split?

## Webhook delivery
**Path/Symbol:** `apps/api/src/services/webhook/delivery.ts`:`WebhookSender` (:49-238) + `webhookEventMatchesFilter` (:32-47) + `logWebhook`/`processWebhookInsertJobs` (:244-300).
**Signature:** `.send<T extends WebhookEvent>(event, data): Promise<WebhookSendResult>` where result = `{attempted, delivered?, queued?, skipped?, statusCode?}`; filter: `(configuredEvents, event): boolean`.
**Data Shape:** payload = `{success, type, id|jobId (v1|v0 naming), webhookId: randomUUID(), data, error?, metadata?}`; signature header `X-Firecrawl-Signature: sha256=<hex hmac-sha256(secret, rawBody)>`; timeouts 30s (v0) / 10s (v1+).

### Decisive source
```ts
const webhookHost = new URL(this.config.url).hostname;
if (isIPPrivate(webhookHost) && config.ALLOW_LOCAL_WEBHOOKS !== true) {
  return { delivered: false, skipped: true };          // SSRF gate BEFORE any fetch
}
if (this.usesWebhookQueue()) { await webhookQueue.publish(queueMessage); return {delivered:false, queued:true}; }
const hmac = createHmac("sha256", this.secret);
hmac.update(payloadString);
headers["X-Firecrawl-Signature"] = `sha256=${hmac.digest("hex")}`;
const res = await undici.fetch(this.config.url, { method:"POST", headers, body: payloadString,
  dispatcher: getSecureDispatcherNoCookies(), signal: abortController.signal });
```

**Flow:** send → global kill-switch (`DISABLE_WEBHOOK_DELIVERY`) + three-way event match (exact / legacy subtype before first dot / namespace suffix after) → SSRF private-IP gate → RabbitMQ path when configured else inline undici POST → BOTH paths append a JSON line to the Redis `webhook-insert-queue`; a batch inserter (`processWebhookInsertJobs`, LPOP up to 1000) bulk-inserts into Postgres `webhook_logs`. Fire-and-forget default: `delivery.catch(() => {})` unless `data.awaitWebhook` — delivery failures NEVER fail the scrape.
**Invariant:** The HMAC is computed over the EXACT serialized body bytes (sign-after-stringify). Log insertion is decoupled from delivery via Redis list + batch inserter so DB outages degrade logging, not delivery. Event filtering must accept all three match shapes or legacy subscribers break.
**Probe:** anchored at repo root `apps/api/src`: `grep -n 'X-Firecrawl-Signature' services/webhook/delivery.ts` → exactly 1 hit at :168; `grep -n 'isIPPrivate(webhookHost)' services/webhook/delivery.ts` → 1 hit at :123; `grep -n 'WEBHOOK_INSERT_BATCH_SIZE = ' services/webhook/delivery.ts` → 1 hit showing 1000.
**Probe:** direct test anchors: `apps/api/src/__tests__/snips/v2/webhook.test.ts` exists (snips suite; runner blocked this window).
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "WebhookSender deliver signature webhook queue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt signed-payload + private-IP gate + queue-or-inline split + buffered log insertion for outbound webhooks; adapt header names/timeouts; omit v0 compatibility fields unless porting an API migration.
