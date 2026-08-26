<!-- capsule-v2 -->
# Webhook HMAC delivery engine — sha256= signature envelope, exponential backoff capped at 30s, fire-and-forget fan-out

**Source:** LinkForty core AGPL-3.0-only `main@8919b1ecdc48f8c53340c4590b5f0eae0680abf8`; Codebase Memory `ext-core`. **Question:** What does a receiver need to verify authenticity, and how do retries and timeouts behave?

## generateWebhookSignature + deliverWebhook + triggerWebhooks
**Path/Symbol:** `src/lib/webhook.ts:generateWebhookSignature` (:7-9), `attemptWebhookDelivery` (:28-90), `deliverWebhook` (:95-134), `triggerWebhooks` (:139-184); secret minted at `generateWebhookSecret` (:14-16) on webhook creation (`src/routes/webhooks.ts:89-90`).
**Signature:** `function generateWebhookSignature(payload: string, secret: string): string` (hex HMAC-SHA256); headers sent: `X-LinkForty-Signature: sha256=<hex>`, `X-LinkForty-Event`, `X-LinkForty-Event-ID`, UA `LinkForty-Webhook/1.0`, plus per-webhook custom headers merged AFTER defaults (override allowed).
**Data Shape:** Payload envelope `{ event, event_id, timestamp, data }` stringified once per attempt; result carries success/status/body(≤1000 chars)/attemptNumber/deliveredAt|errorMessage.

### Decisive source
```ts
// webhook.ts:100,118-123 — retry cadence:
const maxRetries = webhook.retry_count ?? 3;
// Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (capped at 30s)
const delayMs = Math.min(1000 * Math.pow(2, attempt - 1), 30000);
await sleep(delayMs);
// :44-46 + :84-85 — AbortController timeout, abort relabeled:
const timeoutId = setTimeout(() => controller.abort(), webhook.timeout_ms);
errorMessage: error.name === 'AbortError' ? `Timeout after ${webhook.timeout_ms}ms` : ...
```

**Flow:** event producers select active webhooks subscribed to the event (`events.includes(event)` filter :155-157) → `triggerWebhooks` maps deliveries into promises NOT awaited (fire-and-forget; `Promise.all(...).catch(log)` :181-183) → each attempt signs, POSTs with timeout, logs via optional callback whose OWN failure is swallowed → success returns immediately; exhaustion returns a synthetic failure result after the loop.
**Invariant:** Signature = HMAC-SHA256 over the exact raw body bytes with the webhook's stored secret — receivers verify by recomputing over the unparsed body; timeout uses AbortController (fetch-level cancellation), not an external race; logging failures never break delivery loops.
**Probe:** per-file line counts: `bash -c "grep -cF 'sha256=' src/lib/webhook.ts"` → 1 (:38 header template literal); `bash -c "grep -cF 'sha256=' src/routes/webhooks.ts"` → 0 (routes never verify, only the delivery engine signs); direct tests `src/lib/webhook.test.ts`: describe('generateWebhookSignature') determinism/secret-sensitivity cases + describe('deliverWebhook') HTTP 200/500/header cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-core", query: "deliverWebhook signature retry backoff", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the signature-header contract, backoff formula, and unawaited fan-out shape for outbound webhooks; adapt header names/UA; omit custom-header override support if you don't expose it — keep response-body truncation either way (unbounded bodies are a memory hazard).
