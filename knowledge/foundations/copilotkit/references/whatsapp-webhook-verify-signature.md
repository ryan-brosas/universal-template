<!-- capsule-v2 -->
# whatsapp-webhook-verify-signature

## Source
- Repo: `copilotkit` (MIT)
- Path: `packages/channels-whatsapp/src/webhook-server.ts`
- Symbol: `WebhookServer.handleVerify / handlePost / verifySignature`
- Lines: handleVerify :69-80, handlePost :82-109, verifySignature :111-119, health route :42-57
- Commit: `e9387e04835545c45744b791aee7c9c03520be31`
- Graph Node: `ext-copilotkit.packages.channels-whatsapp.src.webhook-server.WebhookServer.verifySignature`

## Question
How does a Meta/Cloud-API webhook server do the subscription handshake and reject forged POSTs while never letting Meta's retry policy turn one slow handler into a disabled webhook?

## Signature & Data Shape
```typescript
verifySignature(raw: Buffer, signature: string | undefined): boolean;
// GET  <path>?hub.mode=subscribe&hub.verify_token=…&hub.challenge=…
// POST <path>  header: x-hub-signature-256: sha256=<hex hmac(appSecret, rawBody)>
```

## Decisive Source Excerpt
```typescript
private verifySignature(raw: Buffer, signature: string | undefined): boolean {
  if (!signature || !signature.startsWith("sha256=")) return false;
  const expected =
    "sha256=" +
    createHmac("sha256", this.args.appSecret).update(raw).digest("hex");
  const a = Buffer.from(signature);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);   // length-gate BEFORE timing-safe compare
}
```
And the ack ordering (:96-105):
```typescript
// Ack immediately; Meta retries non-200 and can disable a flapping webhook.
res.statusCode = 200;
res.end();
let body: WebhookBody;
try { body = JSON.parse(raw) as WebhookBody; } catch { return; }
void this.args.onEvent(body).catch((err) => console.error("[whatsapp] onEvent failed:", err));
```

## Flow
1. **GET handshake:** `hub.mode === "subscribe"` AND exact token match → echo back `hub.challenge` verbatim; otherwise 403.
2. **POST intake:** buffer the raw body; HMAC-SHA256 over the RAW BYTES (not the parsed JSON) with the app secret; compare against `x-hub-signature-256` with a length pre-check then `timingSafeEqual` — mismatch ⇒ 401 before any parsing.
3. **Ack-then-process:** 200 is flushed BEFORE JSON.parse and BEFORE `onEvent` runs; the handler is fire-and-forget with its own catch. A slow/crashing handler therefore can never cause Meta to retry or flap-disable the webhook.
4. Health route: `GET /` returns 200 "ok" for platform probes but is guarded with `path !== "/"` so an operator configuring the webhook at the root doesn't get the health route shadowing the Meta handshake.

## Invariant
Signature verification happens on raw bytes BEFORE parsing and BEFORE the ack; processing happens strictly AFTER the ack; the challenge echo only ever fires for the exact verify token.

## Direct-Test Probe
- File: `packages/channels-whatsapp/src/webhook-server.test.ts`
- Lines: :30 echoes hub.challenge on match; :50 wrong-token verify → 403; :69 correctly-signed POST invokes onEvent; :92 bad signature rejected; :110 correctly-FORMATTED but wrong signature rejected; :133/:150 health route stays narrow

## Graph Query
```bash
codebase-memory-mcp cli search_graph '{"project":"ext-copilotkit","query":"WebhookServer verifySignature hub.challenge timingSafeEqual","limit":10}'
```

## Verdict
Adopt raw-byte HMAC + length-gated timingSafeEqual + ack-before-process + challenge echo. Adapt path/token plumbing per platform. Omit nothing — each ordering choice removes a distinct outage class (forgery, retry-storms, shadowed handshakes).
