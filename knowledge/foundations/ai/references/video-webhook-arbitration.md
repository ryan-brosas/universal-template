<!-- capsule-v2 -->
# Video webhook-vs-polling arbitration — who decides how an async generation completes?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** When a caller passes a webhook factory, which component may accept it, and what must happen after the notification arrives?

## Capability-gated webhook with one-shot post-notification check
**Path/Symbol:** `packages/ai/src/generate-video/generate-video.ts` — arbitration :490–514, start+webhookUrl :516–533, dual-path wait :539–602, `waitForWebhook` :605–640.
**Signature:** `handleWebhookOption({webhook}) => Promise<{webhookUrl: string, received: PromiseLike<OperationWebhook>}>` — OPTIONAL model capability; gateway implementation passes URL/`received` straight through (`gateway-video-model.ts:177–190`).
**Data Shape:** poll defaults `intervalMs ?? 5000`, `timeoutMs ?? 600_000`; early warnings accumulate as `{type:'unsupported', feature:'webhook', details:'…Falling back to polling.'}`.

### Decisive source
```ts
if (webhookFactory != null) {
  if (model.handleWebhookOption != null) {
    const result = await model.handleWebhookOption({ webhook: webhookFactory });
    webhookUrl = result.webhookUrl; webhookReceived = result.received;
  } else {
    earlyWarnings.push({ type: 'unsupported', feature: 'webhook',
      details: 'This model does not support webhooks. Falling back to polling.' });
  }
}
...
if (webhookReceived != null) { await waitForWebhook({...}); }
while (true) {
  if (webhookReceived == null) { /* timeout double-check + delay(intervalMs) */ }
  const statusResult = await retry(() => model.doStatus!({operation, ...}));
  if (statusResult.status === 'error') throw new Error(statusResult.error);
  if (statusResult.status === 'completed') return {...};
  if (webhookReceived != null)
    throw new Error('Video generation did not complete after webhook notification.');
}
```

**Flow:** webhook accepted ONLY if the model implements `handleWebhookOption`; otherwise warn-and-fallback keeps polling semantics. Webhook flow waits for the notification (racing a cancellable timeout so the timer never holds the event loop on success), then performs exactly ONE status call; polling flow loops with delay + double-checked deadline. Gateway's `doStart` maps `webhookUrl` to its `callbackUrl` wire field.
**Invariant:** After a webhook fires there is no second wait — if that one status check isn't completed, it's a hard error ("did not complete after webhook notification"), because a notified-but-incomplete job signals contract failure, not latency. History note: this capability was deliberately ADDED in #19232; before it, the gateway class carried a comment refusing `handleWebhookOption` precisely because accepting webhooks without a delivery channel would hang callers forever.
**Probe:** deterministic probes: `grep -c handleWebhookOption packages/ai/src/generate-video/generate-video.ts` → see battery P16/P17; `grep -c "did not complete after webhook notification" …` → `1`. Direct tests: `generate-video.test.ts` webhook suite (:1836 region) + `start-video.test.ts`.
**Retrieve:** verified live @9d9a73f — search_graph `waitForWebhook handleWebhookOption generate-video` rank#1 = `waitForWebhook :605–640`, rank#3 = `GatewayVideoModel.handleWebhookOption :177–190`.

## Verdict
Adopt capability-probe-then-fallback and the one-shot post-webhook rule; adapt the wire mapping (callbackUrl etc.) per provider; omit the gateway HMAC delivery format unless porting that receiver.
