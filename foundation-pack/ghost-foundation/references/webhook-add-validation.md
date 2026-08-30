<!-- capsule-v2 -->
# Webhook add validation — how is duplicate registration and dangling integration rejected?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What uniqueness and FK semantics must a webhook-creation endpoint reproduce across SQL engines?

## WebhooksService.add
**Path/Symbol:** `ghost/core/core/server/services/webhooks/webhooks-service.js:WebhooksService.add` (:13–53).
**Signature:** `async add(data, options): Promise<Webhook>` where data = `{webhooks: [{event, target_url, integration_id, ...}]}` (single-element array enforced by input validators).
**Data Shape:** Uniqueness = (event, target_url) pair; FK = integration_id → integrations.id; engine-specific constraint errors.
### Decisive source
```js
const webhook = await this.WebhookModel.getByEventAndTarget(data.webhooks[0].event, data.webhooks[0].target_url, options);
if (webhook) { throw new ValidationError({ message: messages.webhookAlreadyExists }); }
try {
  return await this.WebhookModel.add(data.webhooks[0], options);
} catch (error) {
  if (error.errno === 1452 ||
      (error.code === 'SQLITE_CONSTRAINT' && /FOREIGN KEY constraint failed/.test(error.message)) ||
      error.code === 'SQLITE_CONSTRAINT_FOREIGNKEY') {
    throw new ValidationError({ ..., context: `'integration_id' value does not match any existing integration.` });
  }
  throw error;
}
```
**Flow:** pre-check duplicates via targeted query → insert → translate ENGINE-SPECIFIC FK violations (MySQL errno 1452; SQLite two distinct error shapes) into one ValidationError with actionable context; anything else rethrows untouched.
**Invariant:** The FK translation ladder covers THREE shapes because MySQL and two generations of SQLite drivers report the same violation differently — a porter testing on one engine only will ship silent 500s on the others. Duplicate check is advisory (pre-query); a concurrent duplicate still lands in DB-level handling — the pair check exists for UX, not integrity.
**Probe:** `grep -cF "getByEventAndTarget" ghost/core/core/server/services/webhooks/webhooks-service.js` → expect `1`; `grep -cF "errno === 1452" ghost/core/core/server/services/webhooks/webhooks-service.js` → expect `1`; direct tests: `ghost/core/test/unit/server/services/webhooks/webhook-service.test.js` (`it('re-throws any unhandled errors'`) + validator suite `ghost/core/test/unit/api/canary/utils/validators/input/webhooks.test.js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "WebhooksService add validation", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pair-uniqueness pre-check + multi-engine FK error translation. Adapt error codes to host driver matrix; keep rethrow-of-unknown discipline.
