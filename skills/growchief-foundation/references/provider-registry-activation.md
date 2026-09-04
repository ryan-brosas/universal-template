<!-- capsule-v2 -->
# Provider registry activation — how does a plugin-style provider list become a runtime-filtered, name-addressable activity catalog without a DI container?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** how are enrichment providers (and billing/proxy lists) registered, ordered, filtered by configured API keys, and addressed across the Temporal activity boundary?

## Module-level singleton list sorted by priority; `apiKey` getter = activation predicate
**Path/Symbol:** `shared/server/enrichment/provider.list.ts` (whole file); contract `shared/server/enrichment/enrichment.interface.ts`; activity bridge `apps/orchestrator/src/activities/enrichment.activity.ts:EnrichmentActivity` (:8-19).
**Signature:** `providerList = [new RocketReachEnrichment(), new ApolloEnrichment(), new DatagmaEnrichment(), new HunterEnrichment()].sort((a,b) => a.priority - b.priority)`; `EnrichmentInterface = {name, priority, supportedIdentifiers, apiKey?, enrich(platform, params) → EnrichmentReturn | false | {delay}}`.
**Data Shape:** `apiKey` is a GETTER reading `process.env.<PROVIDER>_API_KEY` at call time — never a constructor-injected value — so "is this provider configured?" is evaluated lazily and env-changes apply without rebuilds.

### Decisive source
```ts
// enrichment.activity.ts — Temporal activities address providers BY NAME string:
@ActivityMethod()
async enrich(name: string, platform: string, value: EnrichmentDto) {
  const enrichProvider = providerList.find((p) => p.name === name)!;
  return enrichProvider.enrich(platform, value);
}
@ActivityMethod()
async enrichments() {
  return providerList.filter((f) => f.apiKey);   // activation filter at query time
}
```

**Flow:** workflow boot calls `enrichments()` once per continueAsNew generation → receives ONLY key-configured providers, which sizes `limitsDelay` clocks → dispatch addresses a provider by its display `name` through the generic activity → provider returns url-success / false / `{delay}` backoff.

**Invariant:** three quiet traps: (1) name-based lookup uses `.find(...)!` with NO fallback — renaming a provider's `name` breaks in-flight queues that carry old names in their retry payloads; (2) the activation check happens when the workflow snapshots `enrichments()`, so a key added mid-generation is invisible until the next snapshot — deliberate eventual consistency; (3) `priority` ordering is decided ONCE at module load, making provider tie-break order deterministic but code-order-dependent. The same shape recurs for billing (`shared/server/billing/billing.provider.ts` picks from its own list by name) and proxies (`proxy.list.ts` + `ProxiesManager` find-by-identifier) — it is the repo's repeated extension pattern: plain module-singleton arrays + getter-based activation + string addressing, NOT NestJS DI, because these instances must cross into Temporal activity land as plain data.

**Probe:** deterministic pins from repo root: `grep -nF 'a.priority - b.priority' shared/server/enrichment/provider.list.ts` → last line of list init; `grep -cF 'providerList.filter((f) => f.apiKey)' apps/orchestrator/src/activities/enrichment.activity.ts` → 1; `grep -cF 'p.name === name' apps/orchestrator/src/activities/enrichment.activity.ts` → 1; `grep -cF 'get apiKey()' shared/server/enrichment/providers/rocket.reach.enrichment.ts` → 1 (same pattern ×4 providers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "enrichments activity providerList apiKey filter", limit: 10 });
```

## Verdict
Adopt module-singleton provider arrays with lazy env-getter activation and name-string activity addressing for worker-bound plugins; adapt to your process boundary; omit nothing behavioral. Coverage caveat: deterministic probes only.
