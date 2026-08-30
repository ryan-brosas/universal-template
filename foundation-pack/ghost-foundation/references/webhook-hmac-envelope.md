<!-- capsule-v2 -->
# Webhook HMAC signature envelope — how are outgoing webhook deliveries authenticated?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** What exactly does Ghost sign, with which header format and timestamp binding, so a porter reproduces byte-compatible deliveries verifiers accept?

## Signature envelope in WebhookTrigger.trigger
**Path/Symbol:** `ghost/core/core/server/services/webhooks/webhook-trigger.js:WebhookTrigger.trigger` (:108–158).
**Signature:** `async trigger(event: string, model: Object): Promise<void>`.
**Data Shape:** Per webhook row: `event` (string), `target_url` (string), `secret` (string, may be empty). Payload = `{ event: <webhook's own event name>, ...(await payload(event, model)) }` JSON-stringified once; `ts = Date.now()` per delivery.
### Decisive source
```js
const reqPayload = JSON.stringify(hookPayload);
const ts = Date.now();
const headers = {
  'Content-Length': Buffer.byteLength(reqPayload),
  'Content-Type': 'application/json',
  'Content-Version': `v${ghostVersion.safe}`,
};
if (secret !== '') {
  headers['X-Ghost-Signature'] =
    `sha256=${crypto.createHmac('sha256', secret).update(`${reqPayload}${ts}`).digest('hex')}, t=${ts}`;
}
const opts = {
  method: 'POST', body: reqPayload, headers,
  timeout: { request: 2 * 1000 },
  retry: { limit: process.env.NODE_ENV?.startsWith('test') ? 0 : 5 },
};
await this.request(url, opts).then(response.onSuccess(webhook)).catch(response.onError(webhook));
```
**Flow:** fetch hooks for event → build payload per hook → stringify → sign only if secret non-empty (`HMAC-SHA256(payloadBytes + String(ts))`) → POST with 2s request timeout, got-style retry limit 5 (0 under test) → settle via onSuccess/onError.
**Invariant:** The MAC input is the exact serialized body concatenated with the decimal timestamp string — NOT a canonical re-serialization; the verifier must read raw bytes and the `t=` field from the same header value. Empty secret ⇒ NO signature header at all (not an unsigned timestamp).
**Probe:** `grep -cF "sha256=" ghost/core/core/server/services/webhooks/webhook-trigger.js` → expect `1`; `grep -cE "NODE_ENV\?\.startsWith\('test'\) \? 0 : 5" ghost/core/core/server/services/webhooks/webhook-trigger.js` → expect `1`; direct test pins the full header: `grep -cF "it('uses the request payload and a timestamp to generate the hash in the signature header'" ghost/core/test/unit/server/services/webhooks/trigger.test.js` → expect `1` (reconstructs `expectedHeader` byte-exact under fake timers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "WebhookTrigger trigger", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the envelope contract (header name, `sha256=…, t=<ms>` layout, payload+timestamp MAC input, secret-optional). Adapt timeout/retry numbers to host policy; omit Ghost version header if the porter has no version scheme.
