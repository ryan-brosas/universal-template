<!-- capsule-v2 -->
# Lifecycle broker persisted-cursor subscriptions — how do you deliver cross-agent events at-least-once without redelivering after a restart?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the contract for durable event subscriptions whose progress survives process death?

## Connected graph-selected seam
**Path/Symbol:** `src/lifecycle/broker.ts` — `LifecycleBroker.subscribe` (:92-142), `#drainSubscription` (:210-286), `#sourceIsCurrentOwner` (:288-301), `.publish` (:58-90), `#schedulePoll` (:173-185).
**Signature:** `subscribe({ from, to, events, delivery, triggerTurn, once })` → subscription with `afterSequence: this.mesh.latestSequence()` captured AT SUBSCRIBE TIME (nothing older is ever delivered); `publish(request)` returns the emitted event or `undefined` when unobserved/closed.
**Data Shape:** subscription `format: 1` `{ id: uuid-no-dashes, from, events[], to, delivery, triggerTurn, once, afterSequence, createdAt, updatedAt, createdBy, lastDeliveredAt?, lastEventId?, lastError? }` stored per-key under the lifecycle subscription prefix; validated on read (`entry.key === subscriptionKey(subscription.id)`).

### Decisive source
```ts
      for (const meshEvent of events) {
        const lifecycle = lifecycleEventFromMesh(meshEvent);
        if (!lifecycle) {
          cursor = Math.max(cursor, meshEvent.sequence);
          continue;
        }
        const matches =
          lifecycle.source.id === subscription.from &&
          subscription.events.includes(lifecycle.event) &&
          this.#sourceIsCurrentOwner(lifecycle);
        if (!matches) {
          cursor = lifecycle.sequence;
          continue;
        }
        try {
          await this.deliver(subscription, lifecycle);
        } catch (error) {
          const failed: FabricLifecycleSubscription = {
            ...subscription,
            afterSequence: cursor,             // NOT advanced past the failing event
            updatedAt: Date.now(),
            lastError: error instanceof Error ? error.message : String(error),
          };
          await this.#replace(entry, failed).catch(() => undefined);
          return;                              // retry SAME event next poll
        }
```

**Flow:** publishers are observation-gated — `.publish` first scans existing subscriptions for `(from, event)` interest (`#isObserved`) and skips mesh writes entirely when nobody listens, serializing real publishes on a `#publishTail` promise chain — then `#schedulePoll()` (queueMicrotask + `#pollScheduled` latch, same coalescing shape as topology-refresh-lifecycle). Drain walks EVERY subscription row; rows whose target is absent/stale/non-local are skipped (each host delivers only its own locals). Per event: malformed → cursor advances; non-matching → cursor advances; matching → deliver, and ONLY THEN advance + stamp `lastDeliveredAt`/`lastEventId`. Empty read batches fast-forward `afterSequence` to `latestSequence` (skip-ahead without delivery); `once` subscriptions are deleted right after their first successful delivery.
**Invariant:** at-least-once delivery anchored by PERSISTED cursors — a delivery failure leaves `afterSequence` pointing AT the failing event and records `lastError` (cleared on the next successful pass via `delete updated.lastError`); ownership is re-checked per EVENT (`#sourceIsCurrentOwner` compares participant kind/rootId/runner/ownerHostId/ownerIdentityId against `event.source`) so events from superseded owners never deliver; `subscribe` refuses stale/unknown endpoints, empty event sets, and self-subscription (`from === to`).
**Probe:** `tests/lifecycle-broker.test.ts:96` ("delivers only new matching source events and removes one-shot subscriptions"), `:179` ("persists cursors across broker restarts without redelivering old events").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "LifecycleBroker drainSubscription afterSequence subscription once delivery", limit: 5, fields: ["signature", "name", "file"] });
```
