<!-- capsule-v2 -->
# Fire-and-forget publish recovery — how do you publish to an unresponsive broker without losing wakeups?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How are slow/hung Redis publishes converted into at-least-once delivery guarantees?

## BullMqComputedOutboxWakeupPublisher.publish
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/bullmq-computed-outbox-wakeup.publisher.ts:publish` (:218–252; recovery :291–339; slots :341–352; add options :263–289).
**Signature:** `publish(wakeup): Promise<{status:'accepted'}>`.

### Decisive source
```ts
// :229–232 in-source rationale
// Timeout is intentional fire-and-forget: a slow Redis that still completes
// queue.add after the timeout will deliver the job (at-least-once). The caller
// records timeout/error. Explicit Redis command failures are retried in the background;
// the durable DB row and startup redrive cover process restarts.
await this.withTimeout(operation, this.publishTimeoutMs);
...
removeOnComplete: isDeterministic ? true : { count: COMPUTED_OUTBOX_COMPLETED_RETENTION_COUNT },   // :99–101
```

**Flow:** bounded semaphore (8 concurrent publishes, waiter queue); non-ready client OR timeout/error ⇒ scheduleRecovery keeping THE SAME underlying add-operation promise alive (a hung command may still complete and deliver); single background probe owns recovery — new publishes fail FAST with RecoveryInProgressError rather than piling onto ioredis's offline queue; probe waits exponential-backoff-capped-30s, notifies deliveryRecovered listeners on success; deterministic ids (`cuwr2-*`/`cuwd-*`) removeOnComplete/Fail IMMEDIATELY so they can be re-added after resume; non-deterministic ids retain counts (2000/5000) as history.
**Invariant:** Never cancel an in-flight add on timeout (cancellation could drop a delivery the broker accepted). One recovery circuit per process — concurrent probes would multiply offline-queue pressure. Id-prefix↔retention coupling is what makes redrive replays addable.
**Probe:** `bullmq-computed-outbox-wakeup.publisher.spec.ts` (:126 bounded timeout, :144 bounded recovery circuit + redrive-after-probe, :86/:106 deterministic retention removal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "scheduleRecovery", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fire-and-forget timeouts + single recovery circuit + retention-by-id-class; adapt constants; omit OTel metric calls if undesired.
