<!-- capsule-v2 -->
# Webhook delivery queue — how does an in-memory FIFO survive crashes, fair-share a slow endpoint, and shed load without blocking writes?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you deliver document-triggered HTTP webhooks so a dead consumer never stalls the producer, events aren't lost on process death, and one broken webhook can't starve all others?

## Redis-mirrored FIFO with per-webhook batching and rotate-on-failure
**Path/Symbol:** `app/server/lib/WebhookQueue.ts:WebhookQueue` (whole file, 849L): `enqueue` (162–172), `_startSendLoop`/`_sendLoop` (420–549), `_maxWebhookAttempts` (563–568), `_sendWebhookWithRetries` (570–640), `_getRedisQueue` startup recovery (384–393).
**Signature:** `enqueue(events: WebhookActionPayload[]): Promise<void>`; internal loop consumes `_webHookEventQueue: WebhookActionPayload[]`.
**Data Shape:** event = `{ id: webhookId, payload: RowRecord, action }`; queue key ``webhook-queue-${docId}`` (redis list of JSON strings); knobs `GRIST_MAX_QUEUE_SIZE` (default 1000), `GRIST_TRIGGER_WAIT_DELAY` ms (default 1000), `GRIST_TRIGGER_MAX_ATTEMPTS` (default 20).

### Decisive source
```ts
public async enqueue(events: WebhookActionPayload[]) {
  await this._pushToRedisQueue(events);        // backup FIRST — durable copy before memory
  this._webHookEventQueue.push(...events);
  this._startSendLoop();
  // Prevent further document activity while the queue is too full.
  while (this._drainingQueue && !this._shuttingDown) {   // length >= MAX_QUEUE_SIZE
    const sendNotificationPromise = this._activeDoc.sendWebhookNotification(WebhookMessageType.Overflow);
    const delayPromise = delayAbort(5000, this._loopAbort?.signal).catch(() => {});
    await Promise.all([sendNotificationPromise, delayPromise]);   // BLOCK the producer
  }
}
// one webhook per batch, capped at 100 events, taken only from the head window:
const id = this._webHookEventQueue[0].id;
const batch = _.takeWhile(this._webHookEventQueue.slice(0, 100), { id });
...
this._webHookEventQueue.splice(0, batch.length);       // consume…
if (!success) {
  if (!this._drainingQueue) {
    this._webHookEventQueue.push(...batch);            // …and rotate to the BACK,
    multi.rpush(this._redisQueueKey, ...strings);      // giving other URLs a chance
    await this._stats.logStatus(id, "postponed");
  } else {
    await this._stats.logStatus(id, "error");          // under pressure: drop + mark
    await this._stats.logBatch(id, "rejected");
  }
}
```

**Flow:** enqueue → durable `rpush` to redis → in-memory push → wake single-flight send loop (`_sending` flag; crash of the loop logs + restarts itself) → loop sleeps `TRIGGER_WAIT_DELAY` when idle → head event picks its webhook id → batch = up to 100 consecutive same-id events → fetch URL+secret from TTL-cached home-db secret (10s `MapWithTTL`) → POST via SSRF-guarded `fetchUntrustedWithAgent` with exponential retry (wait doubles 1→2→…→64 units, each unit checks `_shuttingDown`/abort every second) → success ⇒ `splice` head + `ltrim` redis; failure ⇒ requeue-at-tail (memory + `rpush`) or drop-with-status when over `MAX_QUEUE_SIZE` → redis `Multi.execAsync()` runs once after the in-memory mutation settles. On boot, a transient redis client `lrange`s any surviving events and `unshift`s them ahead of fresh ones, then quits — most docs have no triggers so no persistent connection is kept.
**Invariant:** the redis list mirrors every in-memory transition in the SAME order (push-first on enqueue, ltrim/rpush on consume/rotate) so recovery replays exactly the undelivered prefix; producers block (backpressure) instead of dropping while under `MAX_QUEUE_SIZE`, and only cross the threshold by shedding with explicit `rejected` status; batches never mix webhook ids and are capped at 100 so a failing endpoint delays others by rotation, not starvation; a missing/disallowed URL counts as success (event consumed, nothing retried forever); redis errors from the secret store pass through `LogSanitizer.sanitize` before rethrow so connection-string credentials never reach logs.
**Probe:** `test/server/lib/docapi/DocApiWebhooks.ts` `mainWebhooks` suite (:514+: delivery on add/update, non-200 handling incl. 408, deleted-webhook no-call :1039, watched-column filtering :1077) and `/webhooks endpoint › should clear the outgoing queue` (:926); `test/nbrowser/WebhookOverflow.ts` pins the overflow-notification behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "WebhookQueue _sendLoop enqueue", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-write ordering (durable mirror before memory), head-window same-key batching, rotate-on-failure fairness, unit-wise interruptible backoff, and block-then-shed backpressure posture for any per-tenant outbound-event pipeline. Adapt the backing store (any list/stream with range-trim), the secret cache TTLs, and env knob names to host. Omit the ActiveDoc telemetry/notification coupling and the ComposedActionQueue type-routing wrapper unless you also carry email actions — the delivery loop is self-contained.
