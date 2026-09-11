<!-- capsule-v2 -->
# Claim/execute admission & supersession — how do concurrent same-thread deliveries serialize, bound, and hand ownership to a newer claim?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** Multiple runtime instances race for the same channel invitation — what is the claim → one-use-token join → FIFO execution ladder, and how does a newer claim abort an older delivery mid-flight?

## Transport admission ladder with thread-tail serialization and switchable owners
**Path/Symbol:** `packages/channels-intelligence/src/delivery-transport.ts:ChannelDeliveryTransport` (:871-1268): `start` invitation handler (:955-991), `claimAndHandle` (:1041-1207), `acquireExecutionSlot` (:1209-1232) + `executionRelease` (:1234-1247), `stop` (:1026-1039); supersession observer (:1085-1096); capacity overflow (:994-1024).
**Signature:** `start(handler: (claimedDelivery, delivery: PreparedChannelDelivery) => Promise<void>): void`; `private async acquireExecutionSlot(signal): Promise<() => void>`.
**Data Shape:** limits default 8 executing / 32 pending; claim loop retries `deferred` every 50ms; join payload carries one-use `joinToken` + `ownerGeneration`.

### Decisive source
```typescript
// admission: register into active BEFORE any await so stop() waits for this delivery
if (this.active.size >= this.maxConcurrentDeliveries + this.maxPendingDeliveries) {
  this.reportCapacityOverflow(value.deliveryId, value.canonicalThreadId);
  return;
}
const predecessor = this.threadTails.get(value.canonicalThreadId) ?? Promise.resolve();
running = this.claimAndHandle(value.deliveryId, activeHandler, signal, predecessor)
  .finally(() => {
    this.active.delete(value.deliveryId);
    if (this.threadTails.get(value.canonicalThreadId) === running) {
      this.threadTails.delete(value.canonicalThreadId);   // identity-checked delete
    }
  });
this.active.set(value.deliveryId, running);
this.threadTails.set(value.canonicalThreadId, running);

// execution: await the SAME-THREAD predecessor, then take a global slot
await predecessor;
throwIfStopped(claimedDelivery.signal);
releaseExecution = await this.acquireExecutionSlot(claimedDelivery.signal);
await handler(claimedDelivery, delivery);
await claimedDelivery.terminal({ status: "complete", code: "provider_delivery_complete" });
```
```typescript
channel.on("delivery_superseded", (value) => {
  if (isSupersession(value, deliveryId) && claimedDelivery !== undefined) {
    claimedDelivery.supersede(value.supersededByDeliveryId);  // abort("superseded")
  }
});
```

**Flow:** invitation → dedupe by deliveryId → capacity check (overflow is REPORTED to the gateway via `claim_overflow`, never queued silently) → register under `active` synchronously → chain onto the canonicalThread's tail (same-thread work serializes per-thread; Redis still coordinates cross-runtime claims) → claim loop (`deferred` ⇒ 50ms retry) → one-use `join_token` consumed by joining `delivery:<id>` → prepared delivery validated from the join reply → wait predecessor → acquire one of N global execution slots (abort-aware waiter queue; release skips already-aborted waiters) → handler runs → terminal complete; on non-terminal errors send the generic provider message (surface-gated) then `failed_before_output`/`failed` chosen by `hasProviderOutput()` → a newer same-thread claim makes the gateway emit `delivery_superseded`, aborting exactly the old delivery before output.
**Invariant:** The `threadTails` delete must be IDENTITY-CHECKED — a plain delete would drop a newer delivery's tail registration when an older finish lands late. Slot release decrements only when no aborted waiter can inherit the slot.
**Probe:** `packages/channels-intelligence/src/delivery-transport.test.ts` :841 "claims same-Thread work for Redis coordination but executes it in order"; :901 "a newer same-Thread claim aborts the exact switchable delivery before output"; :710 "claims bounded pending work but does not execute above the local limit"; :1212 "stop aborts an active retry wait and leaves its delivery topic". Deterministic anchor `grep -n "threadTails" packages/channels-intelligence/src/delivery-transport.ts | head -3`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "ChannelDeliveryTransport claimAndHandle acquireExecutionSlot threadTails supersede", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-level limiter (per-thread tails + global slots) and explicit overflow reporting for any multi-worker claim system. Adapt limits/deferral cadence to your gateway contract. Omit the identity check in tail cleanup and concurrent same-thread deliveries will interleave.
