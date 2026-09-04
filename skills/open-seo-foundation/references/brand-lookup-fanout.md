<!-- capsule-v2 -->
# Brand lookup fan-out — how do you fan out paid AI-search API calls per platform without overrunning balances, and when do you dare cache the result?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** What runs sequenced vs settled, which errors are blocking, and what gates the cache write?

## Settled platform fan-out with complete-only caching
**Path/Symbol:** `src/server/features/ai-search/services/brandLookup.ts:getBrandLookup` (:51-184), `fetchPlatformData` (:221-289), `rethrowIfBlockingAiSearchError` (:364-377).
**Signature:** `async function getBrandLookup(input: BrandLookupInput, billingCustomer: BillingCustomerContext): Promise<BrandLookupResult>`.
**Data Shape:** Platforms `["chat_gpt", "google"]`; ChatGPT mentions DB is US/en-only (`CHATGPT_LOCATION_CODE`/`CHATGPT_LANGUAGE_CODE` forced); per-platform sub-calls = aggregatedMetrics + topPages + mentionsSearch (limits 20/10/100); cross-aggregated SoV adds one call per platform when competitors exist.

### Decisive source
```ts
// Keep the metered DataForSEO calls sequenced: in hosted mode each
// call checks balance before execution and records spend after, so parallel
// fan-out can overrun a low remaining balance.
for (const platform of PLATFORMS) {
  settled.push(await settle(() => fetchPlatformData(platform, …)));   // await INSIDE loop
}
// Only cache when every call succeeded … must not be frozen for 24h with no way to retry
const allSucceeded = platformBundles.every((b) => b.status === "success" && b.bundle?.complete)
  && crossOutcomes.every((c) => c.status === "success");
```

**Flow:** detect target (brand vs domain) + resolve scope + canonicalize competitors → build param-set cache key → validated cache hit returns early → platforms fetched SEQUENTIALLY (await inside the loop), each platform's three sub-calls settled independently but also awaited in sequence → blocking errors (INSUFFICIENT_CREDITS / AI_SEARCH_BILLING_ISSUE) rethrow immediately; everything else degrades to error-bundles rendered as partial → cross-aggregated competitor comparison per platform, same settle discipline → shape for UI → cache write via waitUntil ONLY if all bundles complete AND result has data.
**Invariant:** Metered calls stay sequenced because each one checks balance pre-execution; parallelism here overruns low balances. A platform whose every sub-call failed rejects so the outer gate refuses to freeze blank data. Partial-but-renderable results are returned uncached so a retry can heal them.
**Probe:** `src/server/features/ai-search/services/brandLookup.test.ts` (partial-failure no-cache + blocking-error propagation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "getBrandLookup fetchPlatformData allSucceeded complete waitUntil setCached", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: sequential metered fan-out, per-sub-call settling with blocking-error passthrough, and never-cache-partial. Adapt platform list and US/en forcing to your provider's coverage. Omit SoV cross-metrics if you don't compare competitors.
