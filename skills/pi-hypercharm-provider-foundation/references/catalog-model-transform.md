<!-- capsule-v2 -->
# Catalog-to-pi model transformation — how do you map a typed provider catalog entry onto the host's Model record without inventing metadata?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** Given a provider API model object (ids, pricing, context limits, attachment flags), what is the exact field-by-field conversion into a pi-usable model record?

## transformApiModel / transformModel
**Path/Symbol:** `index.ts:266-300` (`transformApiModel`), script twin `scripts/update-models.js:238-274` (`transformModel`). Cache-pricing projection inverted at this pass — full contract in cache-pricing-field-remap.md.
**Signature:** `transformApiModel(apiModel: any): JsonModel | null`.
**Data Shape:** in: Charm `/v1/provider` entry (`id`, `name`, `can_reason`, `reasoning_levels[]`, `supports_attachments`, `cost_per_1m_in|out|in_cached`, `context_window`, `default_max_tokens`). out: `JsonModel {id, name, reasoning, thinkingLevelMap?, input[], cost{input,output,cacheRead,cacheWrite}, contextWindow, maxTokens, compat{}}`.

### Decisive source
```ts
if (typeof apiModel.id !== "string" || apiModel.id.length === 0) return null;   // reject id-less entries
...
input: apiModel.supports_attachments === true ? ["text", "image"] : ["text"],
cost: {
	input:      apiModel.cost_per_1m_in || 0,
	output:     apiModel.cost_per_1m_out || 0,
	cacheRead:  apiModel.cost_per_1m_out_cached || 0,   // cached-OUTPUT price
	cacheWrite: apiModel.cost_per_1m_in_cached || 0,    // cached-INPUT price
},
contextWindow: apiModel.contextWindow_or_zero,
maxTokens: apiModel.default_max_tokens || apiModel.context_window || 0,
compat: {
	supportsStore: false,
	supportsReasoningEffort,
	thinkingFormat: "deepseek",
	maxTokensField: "max_tokens",
},
```
(script twin guards each cost with `typeof === 'number'` instead of `||`; offline README uses the stricter variant.)

**Flow:** validate id → derive reasoning surface (levels array filtered to strings ⇒ supportsReasoningEffort; map or on/off fallback) → project attachments → project pricing with zero-fallbacks → limits with `default_max_tokens ?? context_window ?? 0` → stamp fixed compat block.
**Invariant:** missing/absent numeric fields become 0, NOT undefined — downstream arithmetic and display assume numbers. `reasoning` reflects `can_reason === true` STRICTLY (truthy strings fail). The compat defaults encode this OpenAI-completions endpoint family's quirks: store unsupported, deepseek-style thinkingFormat, legacy max_tokens field. Pricing units are $/M as shipped by the API. A null return means "skip silently" — callers `.filter((m): m is JsonModel => m !== null)`. ERRATUM (pass 3): this capsule's pre-drift excerpt showed `cacheRead: in_cached / cacheWrite: 0` with the "no cache-write pricing" comment — upstream commit 49f661b proved that mapping wrong and inverted both twins; see cache-pricing-field-remap.md for the full why. ERRATUM (pass 4): this capsule previously said "script's `convertPricing` rounds to 6 decimals only when normalizing string inputs", implying it participates in the pipeline — call-site census at pin `4520704` proves `convertPricing` (`scripts/update-models.js:150-155`) has ZERO call sites; it is vestigial dead code from a pre-`/v1/provider` era when pricing arrived as strings. The script twin guards costs with `typeof === 'number'` directly and never normalizes strings.
**Probe:** no direct unit test upstream — deterministic probe: models.json (782 lines at HEAD 4520704, committed output of the script twin) doubles as golden fixtures; diff a re-transform against committed rows. Coverage caveat recorded.
**Coverage caveat:** untested upstream; JSON outputs are de-facto snapshot tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "transformApiModel", limit: 5 });
```

## Verdict
Adopt the strict-zero projection and fixed-compat-block pattern for any catalog ingestion. Adapt field names/units to your API contract. Omit Charm-specific compat values if your endpoint differs.
