<!-- capsule-v2 -->
# Webhook SSRF client selection — which HTTP client delivers webhooks and why two exist?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** How does Ghost keep user-registered webhook target URLs from being used to probe internal networks without breaking self-hosted loopback receivers?

## Client choice in WebhookTrigger constructor
**Path/Symbol:** `ghost/core/core/server/services/webhooks/webhook-trigger.js:WebhookTrigger.constructor` (:16–28).
**Signature:** `constructor({ models, payload, request, limitService })`.
**Data Shape:** `request` optional injected client; config flag `security:allowWebhookInternalIPs` (boolean).
### Decisive source
```js
if (request) {
  this.request = request;
} else if (config.get('security:allowWebhookInternalIPs')) {
  this.request = require('@tryghost/request');
} else {
  this.request = require('../../lib/request-external');
}
```
**Flow:** explicit injection wins (tests) → internal IPs allowed ⇒ plain `@tryghost/request` (no IP filtering, works for localhost receivers) → otherwise the SSRF-hardened `request-external` got instance.
**Invariant:** The default for hosted/multi-tenant posture is the FILTERED client; allowing internal IPs is an explicit opt-in flag, never a fallback default. A porter must not collapse the two clients into one or loopback webhook targets silently break / silently become allowed.
**Probe:** `grep -cF "config.get('security:allowWebhookInternalIPs')" ghost/core/core/server/services/webhooks/webhook-trigger.js` → expect `1`; `grep -cF "require('../../lib/request-external')" ghost/core/core/server/services/webhooks/webhook-trigger.js` → expect `1`; direct tests: `grep -cF "uses the external request library when internal IPs disabled in config" ghost/core/test/unit/server/services/webhooks/trigger.test.js` → expect `1`; integration suite `ghost/core/test/integration/services/webhook-request.test.js` carries both branches — `grep -cF "using request-external (allowWebhookInternalIPs: false)" <file>` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "allowWebhookInternalIPs request-external", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way selection ladder with filtered-client-by-default. Adapt the flag name to host config conventions; omit Ghost's specific config module.
