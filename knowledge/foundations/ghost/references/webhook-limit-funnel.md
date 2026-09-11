<!-- capsule-v2 -->
# Webhook plan-limit funnel — how are third-party webhooks suppressed without breaking internal ones?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** When a plan limit on custom integrations trips, which webhook rows still get delivered?

## getAll limit branch in WebhookTrigger
**Path/Symbol:** `ghost/core/core/server/services/webhooks/webhook-trigger.js:WebhookTrigger.getAll` (:30–55).
**Signature:** `async getAll(event): Promise<{ models: Webhook[] }>`.
**Data Shape:** Limit flag name `'customIntegrations'`; webhook→integration relation carries `type` ∈ {internal, core, custom, builtin}.
### Decisive source
```js
async getAll(event) {
  if (this.limitService.isLimited('customIntegrations')) {
    const overLimit = await this.limitService.checkWouldGoOverLimit('customIntegrations');
    if (overLimit) {
      logging.info(`Skipping all non-internal webhooks for event ${event}. ...`);
      const result = await this.models.Webhook.findAllByEvent(event, { context: { internal: true }, withRelated: ['integration'] });
      return { models: result?.models?.filter((m) => m.related('integration')?.get('type') === 'internal') || [] };
    }
  }
  return this.models.Webhook.findAllByEvent(event, { context: { internal: true } });
}
```
**Flow:** two-stage gate — cheap sync `isLimited` first, then async `checkWouldGoOverLimit` only when limited → over-limit ⇒ fetch with integration relation and filter to `integration.type === 'internal'` only.
**Invariant:** The same DB query is used in both paths (`context: { internal: true }`); suppression is a post-fetch FILTER, not a different query — so a porter can't introduce a query-level drift between limited/unlimited behavior. Flag limits use `checkWouldGoOverLimit` because they cannot measure "over"; counting limits could use `checkIsOverLimit`. The same funnel reappears at auth time in api-key admin.js (blocks the API key itself) — dispatch-side and auth-side enforcement are separate layers.
**Probe:** `grep -cF "isLimited('customIntegrations')" ghost/core/core/server/services/webhooks/webhook-trigger.js` → expect `1`; `grep -cF "checkWouldGoOverLimit('customIntegrations')" ghost/core/core/server/services/webhooks/webhook-trigger.js` → expect `1`; `grep -cF "context: { internal: true }" ghost/core/core/server/services/webhooks/webhook-trigger.js` → expect `3` (two in getAll + one in destroy); direct test: `grep -cF "it('does not trigger payload handler when there are hooks registered for an event, but the custom integrations limit is active'" ghost/core/test/unit/server/services/webhooks/trigger.test.js` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "checkWouldGoOverLimit customIntegrations webhook", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-stage limit gate + internal-only filter. Adapt the limit-flag vocabulary; omit Ghost's LimitService internals.
