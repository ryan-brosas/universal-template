<!-- capsule-v2 -->
# Skill discovery prefetch — why did a blocking per-turn skill search move to a per-iteration background probe with one deliberate blocking exception?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you hide auxiliary-retrieval latency under model streaming without starving the one input that has no prior work to hide behind?

## startSkillDiscoveryPrefetch / collectSkillDiscoveryPrefetch
**Path/Symbol:** `src/query.ts:331-335` (start), `:1617-1628` (collect + emit as attachments); module `src/services/skillSearch/prefetch.ts` (feature-gated require `EXPERIMENTAL_SKILL_SEARCH`, query.ts :66-68).
**Signature:** `skillPrefetch?.startSkillDiscoveryPrefetch(null, messages, toolUseContext)` → handle; `await skillPrefetch.collectSkillDiscoveryPrefetch(handle)` → attachment payloads wrapped by `createAttachmentMessage`.
**Data Shape:** per-iteration handle (NOT carried on State — each loop iteration starts a fresh probe; the old one is simply abandoned).

### Decisive source
```ts
// Skill discovery prefetch — per-iteration ... Discovery runs while the
// model streams and tools execute; awaited post-tools alongside the memory
// prefetch consume. Replaces the blocking assistant_turn path that ran inside
// getAttachmentMessages (97% of those calls found nothing in prod). Turn-0
// user-input discovery still blocks in userInputAttachments — that's the one
// signal where there's no prior work to hide under.
const pendingSkillPrefetch = skillPrefetch?.startSkillDiscoveryPrefetch(null, messages, toolUseContext)
```

**Flow:** each iteration kicks the probe BEFORE the API call → collect after tools alongside memory-prefetch drain → emitted as `hidden_by_main_turn`-flagged attachments ("true when the prefetch resolved before this point — should be >98% at AKI@250ms / Haiku@573ms vs turn durations of 2-30s") → pushed into `toolResults` like any attachment.
**Invariant:** (1) turn-0 user-input discovery stays BLOCKING inside the attachment sweep — there is no prior streaming to hide under, so backgrounding it would deliver skills after the model already answered; (2) probes are fire-and-forget: a slow iteration abandons its handle rather than awaiting across iterations; (3) telemetry measures whether hiding works (>98% resolved-before-collect), turning latency-hiding into an observable contract.
**Probe:** coverage caveat (no upstream tests). Deterministic probes: `grep -n "startSkillDiscoveryPrefetch\|collectSkillDiscoveryPrefetch\|hidden_by_main_turn" src/query.ts src/services/skillSearch/prefetch.ts src/utils/attachments.ts | head`; verbatim comment pinned at src/query.ts:323-330.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "startSkillDiscoveryPrefetch", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt measure-then-background for any <1s auxiliary retrieval that succeeds ≥95% of the time; adapt probe cadence; omit the feature-gate indirection if your builds aren't tree-shaken. Porting trap: naively moving ALL skill discovery to background breaks turn-0 quality — the first user prompt has no earlier phase to absorb the wait.
