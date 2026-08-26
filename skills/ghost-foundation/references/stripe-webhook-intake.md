<!-- capsule-v2 -->
# Stripe webhook intake contract — how are signed Stripe events routed and which responses does Stripe expect?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What is the status-code protocol for the inbound Stripe receiver and how do events map to handlers?

## WebhookController.handle
**Path/Symbol:** `ghost/core/core/server/services/stripe/webhook-controller.js:WebhookController` (:3–165; handlers map :18–27; handle :78–113).
**Signature:** `async handle(req, res): Promise<void>`; `configure({ webhookCustomerIgnoreList })`.
**Data Shape:** 8 handled event types → 4 services (subscription ×3 types, invoice.payment_succeeded, checkout.session.{completed, async_payment_succeeded, async_payment_failed}, charge.refunded). Ignore list filters by `event.data.object.customer`.
### Decisive source
```js
if (!req.body || !req.headers['stripe-signature']) { res.writeHead(400); return res.end(); }
let event;
try { event = this.webhookManager.parseWebhook(req.body, req.headers['stripe-signature']); }
catch (err) { logging.error(err); res.writeHead(401); return res.end(); }
...
try { await this.handleEvent(event); res.writeHead(200); res.end(); }
catch (err) { logging.error(`Error handling webhook ${event.type}`, err); res.writeHead(err.statusCode || 500); res.end(); }
```
**Flow:** missing body/signature ⇒ 400 → signature parse failure ⇒ 401 (Stripe retries) → ignore-listed customer on subscription.updated ⇒ **200 without processing** → unknown event type ⇒ silently 200 (`handleEvent` returns when no handler) → handler error ⇒ err.statusCode||500.
**Invariant:** Unknown-type-must-200: registering new Stripe event types upstream must never cause retry storms. The ignore list applies ONLY to customer.subscription.updated — other events for ignored customers still process (deliberate: updates from a migrated-away customer would clobber local state, but deletions/refunds must land). Signature verification lives in WebhookManager.parseWebhook with a secret that is either config-provided (local/stripe-cli mode, no endpoint created) or fetched from the created Stripe endpoint row (network mode).
**Probe:** `grep -cF "shouldIgnoreEvent(event, customerId)" ghost/core/core/server/services/stripe/webhook-controller.js` → expect `2` (call + definition); `grep -cF "res.writeHead(401)" ghost/core/core/server/services/stripe/webhook-controller.js` → expect `1`; direct tests: `grep -cF "it('should ignore customer.subscription.updated events for customers in the ignore list'" ghost/core/test/unit/server/services/stripe/webhook-controller.test.js` → expect `1`; `grep -cF "it('should not handle unknown event type'" ...same` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "WebhookController stripe handlers", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt status-code protocol + typed handler map + update-only ignore list. Adapt handler bodies to host membership logic; keep endpoint provisioning split (config-secret vs created-endpoint secret) if supporting stripe-cli dev mode.
