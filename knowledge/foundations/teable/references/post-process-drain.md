<!-- capsule-v2 -->
# Post-process outbox drain — why does a successful targeted task immediately claim more work?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does one processed seed cascade into its dependent stages without waiting for broker latency?

## drainRemainingOutbox
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-wakeup.handler.ts:drainRemainingOutbox` (:284–335; constants :39–41; invocation :211–217).
**Signature:** `drainRemainingOutbox(worker, workerId, baseId, permit): Promise<void>`.

### Decisive source
```ts
const POST_PROCESS_DRAIN_BATCH_SIZE = 50;
const POST_PROCESS_DRAIN_MAX_TASKS = 500;                       // hard cap
while (drained < POST_PROCESS_DRAIN_MAX_TASKS) {
  permit.assertActive();                                        // abort if slot lost
  const more = await worker.runOnce({ workerId, limit: POST_PROCESS_DRAIN_BATCH_SIZE });
  ...
  if (more.value <= 0) return;                                  // empty poll proves idle
```

**Flow:** after ANY targeted task processes successfully, keep claiming batches of 50 until an empty poll proves THIS worker sees an idle outbox, capped at 500 tasks; every iteration re-asserts the cluster admission permit (lease loss stops the drain mid-flight); errors during drain are WARN-and-return — the original success stands.
**Invariant:** Restores pre-BullMQ polling semantics ("continue after any progress", T6191 comment :212–216): cascade stages enqueue sibling tasks whose delayed wakeups would otherwise add seconds of lag per hop. The empty-poll termination avoids busy-spinning against other workers' concurrent claims.
**Probe:** `computed-outbox-wakeup.handler.spec.ts` (:79 permit held through draining, :106 drain stops on permit loss, :256 drains follow-ups after success).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "drainRemainingOutbox", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt continue-after-progress with cap + permit re-checks; adapt batch size; omit logger shapes.
