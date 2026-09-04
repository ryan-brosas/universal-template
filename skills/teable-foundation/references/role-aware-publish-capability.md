<!-- capsule-v2 -->
# Role-aware publisher capability — how do you let consumers emit queue messages in producer-disabled deployments?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is producer/consumer role separation enforced for REPLAY publishes that only consumers legitimately make?

## createRoleAwareWakeupPublisher
**Path/Symbol:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-wakeup-producer.module.ts:createRoleAwareWakeupPublisher` (:260–278; provider wiring :281–300).
**Signature:** `(publisher, {producerEnabled, consumerEnabled}) => IComputedOutboxWakeupAppPublisher`.

### Decisive source
```ts
const consumerScope = new AsyncLocalStorage<boolean>();
return {
  publish: async (wakeup) => {
    const consumerCanPublish = roles.consumerEnabled && consumerScope.getStore() === true;
    if (!roles.producerEnabled && !consumerCanPublish) {
      return { status: 'disabled' as const };
    }
    return publisher.publish(wakeup);
  },
  runAsConsumer: (operation) => consumerScope.run(true, operation),
```

**Flow:** AsyncLocalStorage carries an explicit "acting-as-consumer" flag; plain publishes are gated on producerEnabled; publishes wrapped in `runAsConsumer(...)` are allowed when consumerEnabled — this is how deferred replays, final-attempt re-arms, redrives, and anomaly recoveries work in consumer-only pods. Disabled path returns typed `{status:'disabled'}` instead of throwing.
**Invariant:** The flag is EXPLICIT (callers opt into consumer scope at each replay site — spec "runs worker-created wakeups inside the consumer publish capability") rather than inferred from call stack; producer-disabled deployments therefore cannot leak publishes from business code paths.
**Probe:** `apps/nestjs-backend/src/features/v2/computed-outbox-trigger/computed-outbox-wakeup.handler.spec.ts` (:546 worker-created wakeups in consumer capability, :568 consumer-only deferred replays).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "createRoleAwareWakeupPublisher", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ALS-scoped consumer capability; adapt to your context-propagation lib; omit the factory-provider indirection.
