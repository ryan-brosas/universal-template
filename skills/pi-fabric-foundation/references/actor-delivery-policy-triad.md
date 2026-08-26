<!-- capsule-v2 -->
# Delivery policy triad — how do you route agent output to a live conversation without letting background agents wake the user's session?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** which delivery modes may start the main turn, and where is that rule enforced so callers cannot misuse `triggerTurn`?

## Active/passive split with construction-time validation
**Path/Symbol:** `src/actors/delivery-policy.ts` whole file (:1-47); enforcement at create/setDeliveryPolicy in `src/actors/manager.ts:267,456`; labeling at :35-46.
**Signature:** `resolveActorDeliveryPolicy(delivery?, triggerTurn?): {delivery, triggerTurn}`; `actorDeliveryNotice(delivery, triggerTurn): string|undefined`.
**Data Shape:** `delivery ∈ {"steer","followUp","mailbox","nextTurn"}`; active set = steer/followUp (interrupt or queue onto a running Main), passive set = mailbox/nextTurn.

### Decisive source
```ts
if (ACTIVE_DELIVERIES.has(resolvedDelivery)) {
  if (typeof triggerTurn !== "boolean") {
    throw new Error(`Actor delivery "${resolvedDelivery}" requires explicit triggerTurn: true or false`);
  }
  return { delivery: resolvedDelivery, triggerTurn };
}
if (triggerTurn === true) {
  throw new Error(`Actor delivery "${resolvedDelivery}" cannot use triggerTurn: true because it never starts Main`);
}
return { delivery: resolvedDelivery, triggerTurn: false };
```

**Flow:** every create/policy-update funnels through this one resolver → active modes force an EXPLICIT boolean (no default — silence is a type error) → passive modes hard-reject `triggerTurn:true` because they can never start Main → at delivery time the host skips enqueueing when `delivery==="mailbox"`, and `actorDeliveryNotice` stamps bracketed explanations onto deferred/passive messages so the model knows why its output did not surface.
**Invariant:** "never starts Main" is enforced at construction, not at send time; the explicitness requirement means a porter cannot silently pick a default for interrupt-capable modes. The resident-host layer re-checks (`delivery === "nextTurn" ? false : triggerTurn`) when translating actor deliveries into its own queue.
**Probe:** `tests/actor-delivery-policy.test.ts:8` ("makes active turn intent explicit"), :22 ("rejects trigger intent for delivery modes that never start Main"), :31 ("labels passive and deferred deliveries without labeling active continuations"); end-to-end: `tests/residency.test.ts:323` ("queues passive actor delivery until Main resumes").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "resolveActorDeliveryPolicy triggerTurn mailbox", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-mode vocabulary and construction-time mutual exclusion for any supervisor that can both interrupt and buffer; adapt mode names to your UX verbs; omit the notice strings if your transport labels deliveries elsewhere. Direct tests pin all three rules — no coverage caveat.
