<!-- capsule-v2 -->
# Webhook dispatch fan-out — how do you deliver one event to N subscriber URLs without one bad recipient killing the batch?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** When one business event must reach many registered webhook endpoints over an async queue, what does the enqueue boundary return and what must never throw?

## sendWebhooks fan-out over Promise.allSettled
**Path/Symbol:** `apps/web/lib/webhook/qstash.ts:sendWebhooks` (23-59), helper `publishWebhookEventToQStash` (62-129); entry wrapper `apps/web/lib/webhook/publish.ts:sendWorkspaceWebhook` (8-45).
**Signature:** `sendWebhooks({ webhooks: Pick<Webhook,"id"|"url"|"secret">[], trigger: WebhookTrigger, data: WebhookEventPayload }): Promise<WebhookEnqueueResult[]>`
**Data Shape:** `WebhookEnqueueResult = { webhookId: string; ok: boolean; messageId?: string; error?: unknown }`. Input webhooks are narrowed to exactly three columns (`id/url/secret`) — the DB row is never leaked into the queue layer.

### Decisive source
```ts
if (webhooks.length === 0) {
  return [];
}

const payload = prepareWebhookPayload(trigger, data);

const results = await Promise.allSettled(
  webhooks.map((webhook) =>
    publishWebhookEventToQStash({ webhook, payload }),
  ),
);

return results.map((result, i) => {
  if (result.status === "fulfilled") {
    return { webhookId: webhooks[i].id, ok: true, messageId: result.value.messageId };
  }
  return { webhookId: webhooks[i].id, ok: false, error: result.reason };
});
```

**Flow:** caller resolves subscribers → `prepareWebhookPayload` builds ONE envelope shared by all recipients (`{id: evt_<nanoid25>, event, data, createdAt}`) → each recipient published independently → per-recipient failures become `ok:false` rows, never rejections.
**Invariant:** the function NEVER rejects for a single recipient failure; a failed enqueue is data (`ok:false, error`), not an exception. Empty input returns `[]` before any I/O. One shared event id means all recipients receive the same `eventId`, which is what the delivery-callback route uses to correlate.
**Probe:** `apps/web/tests/webhooks/index.test.ts` (integration: `testWebhookEvent` asserts `results[0].ok === true` and a real `messageId`, then fetches the QStash message back and checks url/method/callback params/body schema — lines 112-158). No unit-level failure-injection test exists upstream; porters must add their own probe for the `ok:false` path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "sendWebhooks publishWebhookEventToQStash webhook fan-out", limit: 10 });
// graph: sendWebhooks has 57 inbound callers (every event emitter in app/(ee)); trace_path --function-name sendWebhooks --direction inbound
```

## Verdict
Adopt the allSettled fan-out contract: per-recipient result objects, shared event envelope, zero-column secret-bearing input shape, empty-input short circuit. Adapt the transport (QStash publishJSON → your queue's publish) and the `delay: 5` test-mode knob. Omit dub's receiver-specific payload transforms (slack/segment) unless your subscribers need dialects. Coverage caveat: only the happy path has a direct integration test.
