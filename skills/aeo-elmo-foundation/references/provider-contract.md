<!-- capsule-v2 -->
# Provider contract — what must a new answer-engine adapter implement?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** What is the single interface every tracking surface (scraped consumer UI or direct model API) implements, and how do callers tell them apart?

## The Provider SPI
**Path/Symbol:** `packages/lib/src/providers/types.ts:Provider` (L52–83), `ScrapeResult` (L10–16); registry wiring in `packages/lib/src/providers/index.ts` (providerMap L28–39).
**Signature:** `run(model, prompt, options?: { webSearch?, version? }): Promise<ScrapeResult>`; optional `accessFor?(config): ProviderAccess`, `validateTarget?(config): string | null`, `runStructuredResearch?<T>(opts: { prompt, schema: z.ZodType<T>, webSearch? }): Promise<{ object: T, modelVersion? }>`; required `id`, `name`, `access`, `isConfigured()`.
**Data Shape:** every run normalizes to `ScrapeResult = { textContent, rawOutput, webQueries, citations: Citation[], modelVersion? }` — the raw provider payload is stored verbatim (`rawOutput`) alongside the normalized fields so later extraction improvements re-read history without re-paying for runs.

### Decisive source
```ts
export type ProviderAccess = "scraped" | "api";
// "scraped": the consumer product is driven and its rendered answer read back…
// "api": the model is called directly … web grounding only happens when the
// model has a search tool and it is switched on.
export function isGroundedApiTarget(config: ModelConfig): boolean {
	return config.webSearch && resolveProviderAccess(config) === "api";
}
```
(`resolveProviderAccess` = `provider.accessFor?.(config) ?? provider.access` — per-target refinement wins over the provider default.)

**Flow:** worker resolves `getProvider(config.provider)` from a static map; unknown ids THROW (`Unknown provider:`) rather than degrade. The scraped/api distinction is not cosmetic — billing tiers, premium-pool membership, and the settings-page label all derive from `isGroundedApiTarget`.
**Invariant:** `webSearch && access === "api"` is the definition of the expensive grounded call; a scraped target is ALWAYS "online" because the consumer surface searches by itself. Porters who treat any web-search target as grounded double-bill.
**Probe:** `packages/lib/src/providers/coverage.test.ts` ("how a target is reached" describe — pins `dfs("chatgpt") === "scraped"`, `dfs("chatgpt","gpt-5") === "api"`, Perplexity = api because it has no scraper route).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "isGroundedApiTarget resolveProviderAccess getProvider ScrapeResult", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-value access model + ScrapeResult normalization as-is — it is what lets nine heterogeneous providers feed one metrics pipeline; adapt the optional-method surface to your needs; omit the docsAnchor/status-page plumbing.
