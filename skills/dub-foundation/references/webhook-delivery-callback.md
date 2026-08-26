<!-- capsule-v2 -->
# Webhook delivery-status callback — how do you learn a queued delivery failed and turn repeated failures into automatic disabling?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** After handing deliveries to an async queue, how does the system correlate queue callbacks back to a webhook row, decide failure vs success, and escalate consecutive failures?

## QStash callback route + failure ladder
**Path/Symbol:** `apps/web/app/api/webhooks/callback/route.ts:POST` (22-104); ladder `apps/web/lib/webhook/failure.ts:handleWebhookFailure` (12-63) / `resetWebhookFailureCount` (65-73); thresholds `apps/web/lib/webhook/constants.ts:51-52`.
**Signature:** `handleWebhookFailure(webhookId: string): Promise<void>`; callback POST takes no args (raw Request).
**Data Shape:** callback query params `{webhookId, eventId, event, failed?: "true"}` validated by zod; callback body is QStash's `{url, status, body, sourceBody, sourceMessageId}` with base64-encoded request/response bodies. Webhook columns: `consecutiveFailures: int`, `lastFailedAt`, `disabledAt`.

### Decisive source
```ts
const isFailed = status >= 400 || status === -1;
// ...
await Promise.allSettled([
  recordWebhookEvent({ url, event, event_id: eventId,
    http_status: status === -1 ? 503 : status, /* ... */ }),
  // Handle the webhook delivery failure if it's the last retry
  ...(isFailed ? [handleWebhookFailure(webhookId)] : []),
  // Only reset if there were previous failures
  ...(webhook.consecutiveFailures > 0 && !isFailed
    ? [resetWebhookFailureCount(webhookId)] : []),
]);
```
```ts
// failure.ts — increment-then-branch ladder
if (webhook.disabledAt) return;                                  // already off → stop
if (WEBHOOK_FAILURE_NOTIFY_THRESHOLDS.includes(consecutiveFailures)) {  // 5/10/15
  await notifyWebhookFailure(webhook); return;                   // warn only
}
if (webhook.consecutiveFailures >= WEBHOOK_FAILURE_DISABLE_THRESHOLD) { // 20
  const updatedWebhook = await prisma.webhook.update({ data: { disabledAt: new Date() } });
  await Promise.allSettled([notifyWebhookDisabled(updatedWebhook),
                            syncWorkspaceWebhookStatus(webhook.projectId)]);
}
```

**Flow:** queue calls the callback after final retry (success or exhaustion) → signature verified (`verifyQstashSignature`) → params+body parsed → unknown webhookId returns 200-with-log (never errors) → four side effects run under one `Promise.allSettled`: event recording, failure handling when `status>=400 || -1`, counter reset on first success, payout-event triage. The failure handler increments atomically in the same UPDATE that reads the new count, then branches: disabled-already → noop; count ∈ {5,10,15} → owner email; count ≥ 20 → set `disabledAt` + notify + recompute workspace flag.
**Invariant:** the increment and its read are ONE atomic update — never fetch-then-write the counter (lost-update race). A webhook already `disabledAt` never gets duplicate emails. Reset runs ONLY when `consecutiveFailures > 0`. Every post-callback side effect is individually best-effort (`allSettled`): analytics failing must not block disabling. The callback always answers 200 — a failing endpoint must not cause the queue to retry the receipt itself.
**Probe:** no upstream unit test for the callback or ladder (`tests/webhooks/index.test.ts` covers enqueue-side only) — coverage caveat. Deterministic probe: constants pin `WEBHOOK_FAILURE_NOTIFY_THRESHOLDS = [5,10,15]`, `WEBHOOK_FAILURE_DISABLE_THRESHOLD = 20`; porters should test increment→notify@5→disable@20 against a fake Prisma.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "handleWebhookFailure resetWebhookFailureCount webhook callback", limit: 10 });
```

## Verdict
Adopt the whole pattern: queue-level callbacks carrying correlation params, base64 body echo for observability, atomic increment-then-branch escalation ladder, reset-on-first-success, allSettled side effects, always-200 receipts. Adapt thresholds/emails to your product; adapt `status === -1 → 503` mapping to your queue's sentinel. Omit the Zapier 410 auto-unsubscribe and payout-specific handling unless you have equivalent integrations.
