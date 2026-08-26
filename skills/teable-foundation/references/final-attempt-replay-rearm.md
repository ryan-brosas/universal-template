<!-- capsule-v2 -->
# Final-attempt replay re-arm — how do you bridge BullMQ attempt exhaustion to a durable outbox safety net?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What must happen when the LAST in-broker retry of a wakeup fails?

## BullMqComputedOutboxWakeupProcessor.process
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/bullmq-computed-outbox-wakeup.processor.ts:BullMqComputedOutboxWakeupProcessor.process` (:20–58).
**Signature:** `process(job: Job<unknown>): Promise<void>`.

### Decisive source
```ts
const parsed = computedOutboxWakeupWireSchema.safeParse(job.data);
if (!parsed.success) {
  this.metrics.recordConsume('invalid');
  throw new UnrecoverableError('Invalid computed outbox wake-up payload');   // :34 no retry
}
...
} catch (error) {
  const maxAttempts = job.opts.attempts ?? 1;
  if (job.attemptsMade + 1 >= maxAttempts) {                                 // :41 final attempt?
    await this.wakeupPublisher.runAsConsumer(() => this.wakeupPublisher.publish(
      createComputedOutboxWakeup({ taskId, baseId,
        availableAt: new Date(Date.now() + 30_000), cause: 'replay' }))).catch(() => undefined); // :42–53
```

**Flow:** Zod-validate the versioned wire payload FIRST — schema violations throw UnrecoverableError so poison messages are parked by BullMQ, not retried; execution errors rethrow (broker retries) BUT on the FINAL attempt also publish a 30s-delayed `cause:'replay'` wakeup whose durable DB row outlives broker state; the re-arm publish itself is best-effort (`.catch(() => undefined)`) because startup redrive is the ultimate net.
**Invariant:** Validation-before-business-logic keeps malformed payloads from consuming retries; the durable-row + broker-job duality means neither system alone needs perfect delivery. Re-arm delay (30s) exceeds typical transient outage windows.
**Probe:** `bullmq-computed-outbox-wakeup.processor.spec.ts` ×3 (:11 valid forwards, :33 invalid→UnrecoverableError + recordConsume('invalid'), :47 final-attempt publishes replay).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "UnrecoverableError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate-first + final-attempt durable re-arm; adapt wire schema fields; omit NestJS processor decorator.
