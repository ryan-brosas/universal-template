<!-- capsule-v2 -->
# ComposedActionQueue — how do you route trigger events to different executors by action type without coupling them?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How does one producer fan events out to per-type queues (webhook vs email) with type-safe registration and honest error aggregation?

## Group-by-discriminator fan-out over an ActionQueue interface
**Path/Symbol:** `app/server/lib/WebhookQueue.ts:ActionQueue/ComposedActionQueue` (68–114); registered consumers in `app/server/lib/Triggers.ts` (`DocActionsHandler` wires `.use("webhook", webhookQueue)`).
**Signature:** `use<K extends keyof ActionPayloadMap>(type: K, queue: ActionExecutor<ActionPayloadMap[K]>)`; `enqueue(events: ActionPayload[]): Promise<void>`; `ActionExecutor<T> = ActionQueue<T> | ((events: T[]) => Promise<void>)`.
**Data Shape:** `ActionPayload = { id, payload: RowRecord, action: TriggerAction }` discriminated on `action.type: "webhook" | "email"`; `_queueMap: Map<string, ActionQueue<ActionPayload>>`.

### Decisive source
```ts
public use<K extends keyof ActionPayloadMap>(type: K, queue: ActionExecutor<ActionPayloadMap[K]>) {
  if (typeof queue === "function") {
    this._queueMap.set(type, { enqueue: queue });   // bare fn adapts to the interface
  } else {
    this._queueMap.set(type, queue);
  }
}
public async enqueue(events: ActionPayload[]) {
  const eventsByType = _.groupBy(events, e => e.action.type);
  const promises: Promise<void>[] = [];
  for (const [type, typeEvents] of Object.entries(eventsByType)) {
    const queue = this._queueMap.get(type);
    if (queue) { promises.push(queue.enqueue(typeEvents)); }
    else { log.warn("ComposedActionQueue: no queue for action type", type); }   // skip, don't crash
  }
  await Promise.allSettled(promises);
  await Promise.all(promises);   // Rethrow any errors — AFTER all queues settled
}
```

**Flow:** one call site (the trigger handler) hands the whole event batch to the composer → events are grouped by their action discriminator → each group goes to its registered queue concurrently → unknown types log a warning and are DROPPED silently-with-trace rather than failing the document write → errors from individual queues are collected via allSettled and rethrown together only after every queue has finished, so a slow/failing email queue can't cancel in-flight webhook dispatch mid-batch.
**Invariant:** producers never know consumer types; consumers register under a string key that must match the action's `type` discriminant; per-group isolation is temporal (all groups still run concurrently — ordering across types is undefined); the double-await (allSettled then all) is the error-aggregation trick: no unhandled rejections, but failures DO propagate to the caller once everything drained.
**Probe:** exercised through `test/server/lib/docapi/DocApiWebhooks.ts` end-to-end (webhook registration path) and `test/server/lib/Triggers.ts` trigger-dispatch suites; no isolated ComposedActionQueue unit file (coverage caveat noted).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "ComposedActionQueue ActionQueue enqueue", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt when a single domain event stream feeds multiple delivery backends (webhooks + email + future sinks): ~30 lines buys open/closed extension — new sink = one `.use()` line. Adapt the payload map and grouping key to your discriminant. Omit if you have exactly one executor; the abstraction pays for itself only from the second consumer.
