<!-- capsule-v2 -->
# Enrichment provider failover — how do multiple paid enrichment providers share load with per-provider backoff and per-item memory of failures?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** four providers, each with its own rate limits and API key; how does one queue item try them in order without burning a provider that just returned 429?

## limitsDelay (provider clock) × testedProviders (item memory)
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.enrichment.ts:workflowEnrichment` (:31-198); providers `shared/server/enrichment/providers/*.enrichment.ts`; contract `shared/server/enrichment/enrichment.interface.ts`.
**Signature:** `workflowEnrichment({ queue?, limitsDelay? })` — BOTH carried across continueAsNew; `enrich(providerName, platform, item): Promise<EnrichmentReturn | false | { delay: number }>`; `EnrichmentInterface = { name, priority, supportedIdentifiers, apiKey?, enrich() }` with `providerList` sorted by priority at module load.
**Data Shape:** `limitsDelay: { name: string; delay: number }[]` — absolute "available-at" ms timestamps per provider, re-seeded to `Date.now()` when the array length ≠ provider count (config-change detector); `queue[].testedProviders: string[]` grows per failed attempt.

### Decisive source
```ts
const availableProviders = limitsDelay.filter((p) => p.delay <= now);
if (availableProviders.length === 0) {
  await sleep(Math.min(...notAvailableProviders.map((l) => l.delay - Date.now())) + 1000);
  continue;
}
const availableQueues = queue.filter((item) =>
  availableProviders.some((p) => !item.testedProviders.includes(p.name)));
// ...credit check: monthlyCredits - used === 0 ⇒ silently drop item from queue
for (const provider of goOver...) {
  const value = await enrich(provider.name, item.platform, item);
  if ((value === false && item.testedProviders.length === enrichmentList.length - 1) ||
      (value && 'url' in value)) {
    try { await externalHandle.signal(finishedEnrichment, { stepId: item.stepId, value });
          if (value) await consumeCredits(item.organizationId, 1); } catch (err) {}
    // splice item; break
  }
  if (!value) item.testedProviders.push(provider.name);            // remember failure
  if (value && 'delay' in value)
    limitsDelay[...].delay = Date.now() + value.delay;             // 429 backoff
}
```

**Flow:** pick head item whose untested ∩ available set is non-empty → credit gate → try providers one by one: success or last-provider-exhausted terminates the item (signaling `false` so the campaign stops waiting); `false` marks the provider tested FOR THAT ITEM; `{delay}` puts the whole PROVIDER on cooldown (RocketReach maps HTTP 429 body `wait` seconds → ms).
**Invariant:** terminal condition is exactly `success OR tested every provider` — checked via `testedProviders.length === enrichmentList.length - 1` BEFORE pushing the final failure, because the signal must carry the definitive false only once; credits are consumed ONLY on successful url results, and an out-of-credits org's item is dropped without any signal (the campaign's `condition` would hang forever if the drop weren't paired with the exhausted-providers terminal path — dropping happens only after all providers were tried).
**Probe:** no test runner upstream. Deterministic pins: `grep -n 'testedProviders' apps/orchestrator/src/workflows/workflow.enrichment.ts` → :18/:48/:70/:88/:101/:106/:121/:127/:135/:146/:158/:191; 429 mapping `grep -n 'req.status === 429' shared/server/enrichment/providers/rocket.reach.enrichment.ts` → :44.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "limitsDelay testedProviders consumeCredits", limit: 10 });
```

## Verdict
Adopt: two-dimensional failover (provider-level cooldown clock + item-level tried-set), priority-ordered provider list filtered by configured apiKey presence. Adapt the terminal-condition arithmetic to your provider count. Omit vendor request/response shapes.
