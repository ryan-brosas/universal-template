<!-- capsule-v2 -->
# Stripe webhook endpoint reconciliation — how does the remote webhook endpoint stay provisioned across reconnects?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What idempotent create/update/recover ladder keeps the Stripe endpoint row matching reality?

## WebhookManager.setupWebhook
**Path/Symbol:** `ghost/core/core/server/services/stripe/webhook-manager.js:WebhookManager.setupWebhook` (:127–163; mode field :37; local mode :106–113; static events list :44–53).
**Signature:** `async setupWebhook(id?: string, secret?: string, opts?: {forceCreate?, skipDelete?}): Promise<{id, secret}>`.
**Data Shape:** `mode: 'network'|'local'` — config `webhookSecret` present ⇒ local (stripe-cli; NO endpoint created); else network. Static event subscription list mirrors the controller handlers exactly.
### Decisive source
```js
} catch (err) {
  if (err.code === 'resource_missing') {
    return this.setupWebhook(id, secret, { skipDelete: true, forceCreate: true });
  }
  return this.setupWebhook(id, secret, { skipDelete: false, forceCreate: true });
}
```
**Flow:** have id+secret and not forceCreate ⇒ try UPDATE endpoint → resource_missing (deleted remotely) ⇒ recreate WITHOUT delete attempt → other update error ⇒ delete-then-recreate. No id/secret ⇒ optional delete of stale id then CREATE.
**Invariant:** Recursion-with-flag recovery: each failure mode picks a different retry posture but always terminates in a created endpoint. `stop()` and endpoint deletion are no-ops in local mode — config-supplied secrets are never remotely deleted. The 8-event static list is the contract twin of WebhookController.handlers — drift between them silently drops events.
**Probe:** `grep -cF "this.mode = 'local'" ghost/core/core/server/services/stripe/webhook-manager.js` → expect `1`; `grep -cF "resource_missing" ghost/core/core/server/services/stripe/webhook-manager.js` → expect `1`; direct test coverage lives in `ghost/core/test/unit/server/services/stripe/webhooks/*event-service.test.js` for handler bodies; manager itself is exercised via controller tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "setupWebhook forceCreate resource_missing", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the update→recreate ladder with distinct resource_missing handling and local-mode short-circuit. Adapt to host payment provider SDK error codes.
