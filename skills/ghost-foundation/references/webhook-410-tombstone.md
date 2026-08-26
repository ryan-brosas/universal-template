<!-- capsule-v2 -->
# Webhook 410 tombstone — when does a failed delivery delete the subscription itself?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** How should a dispatcher react to receiver status codes so dead endpoints are pruned but transient failures never lose a webhook?

## onError / update / destroy in WebhookTrigger
**Path/Symbol:** `ghost/core/core/server/services/webhooks/webhook-trigger.js:WebhookTrigger.onError` (:86–106; with `update` :57–68, `destroy` :70–76).
**Signature:** `onError(webhook): (err) => void` where err carries `statusCode`, `code`, `message`.
**Data Shape:** Webhook row columns written on every attempt outcome: `last_triggered_at` (ms epoch), `last_triggered_status`, `last_triggered_error` (string or null).
### Decisive source
```js
onError(webhook) {
  return (err) => {
    if (err.statusCode === 410) {
      logging.info(`Webhook destroyed (410 response) for "${webhook.get('event')}" ...`);
      return this.destroy(webhook);
    }
    this.update(webhook, { statusCode: err.statusCode, error: `Request failed: ${err.code || 'unknown'}` });
    logging.error(`[WEBHOOK_DELIVERY_FAILURE] url=${...} status=${...} error_code=${...} message=${...}`, err);
  };
}
```
**Flow:** delivery settles → success path writes `last_triggered_*` via fire-and-forget `.edit().catch(warn)` → 410 Gone ⇒ destroy the webhook row entirely (receiver's explicit statement "this subscription is gone") → any other failure only records status/error + structured log.
**Invariant:** ONLY 410 deletes. Timeouts (no statusCode), 5xx, DNS errors — everything else must leave the webhook registered. `update`/`destroy` failures are swallowed to warnings; telemetry write failures must never throw into the event-emitter dispatch loop (which has no catcher).
**Probe:** `grep -cF "statusCode === 410" ghost/core/core/server/services/webhooks/webhook-trigger.js` → expect `1`; `grep -cF "WEBHOOK_DELIVERY_FAILURE" ghost/core/core/server/services/webhooks/webhook-trigger.js` → expect `1`; `grep -cF "last_triggered_status" ghost/core/core/server/services/webhooks/webhook-trigger.js` → expect `1`; direct test: `grep -cF "it('logs a structured error for failed webhook deliveries'" ghost/core/test/unit/server/services/webhooks/trigger.test.js` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "onError statusCode 410 destroy webhook", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 410-tombstone rule and last_triggered bookkeeping as the delivery-lifecycle contract. Adapt log format; omit Ghost-specific model layer (`Webhook.edit/destroy`) in favor of host persistence.
