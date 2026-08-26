<!-- capsule-v2 -->
# Zero-cost subscription model catalog — what does a ProviderModelConfig row look like when the plan is subscription-metered, not pay-per-token?

**Source:** pi-bailian MIT `main@c26c4e9855c87b18b17d5717b8c9171a27031d06`; Codebase Memory `pi-bailian`. **Question:** How do I encode model capability/limit data for a flat-rate subscription plan so host cost math stays honest?

## Catalog-row shape seam
**Path/Symbol:** `src/models.ts:bailianModels` (:16-98), `bailianModelsCN` (:104-186), pricing rationale in header comment (:3-15).
**Signature:** `export const bailianModels: ProviderModelConfig[]`.
**Data Shape:** 9 rows; each `{id, name, reasoning: boolean, input: ("text"|"image")[], cost: {input, output, cacheRead, cacheWrite}, contextWindow, maxTokens}`.

### Decisive source
```ts
 * Pricing: $50/month (Pro plan)
 * - 6,000 requests per 5 hours (sliding window)
 * - 45,000 requests per week (resets Monday 00:00 UTC+8)
 * - 90,000 requests per month (resets on subscription date)
 *
 * Note: Cost is set to 0 as this is a subscription-based plan, not pay-per-token.
 * Model data sourced from https://models.dev/api.json
 ...
 {
   id: "qwen3.5-plus",
   name: "Qwen3.5 Plus",
   reasoning: true,
   input: ["text", "image"],
   cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
   contextWindow: 1000000,
   maxTokens: 65536,
 },
```

**Flow:** static catalog arrays are imported by the registration seam and handed to the host wholesale; per-model limits (`contextWindow`, `maxTokens`) vary by vendor model (1M/65k for Qwen plus-tier down to 196k/24k for MiniMax), while `cost.* = 0` uniformly signals "already paid". The REAL metering contract lives in the header doc comment as three request windows (5h sliding / weekly Monday 00:00 UTC+8 reset / monthly subscription-date reset) — request quotas, not token math. Vendor composition: 4 Qwen + 2 GLM + 1 Kimi + 1 MiniMax + 1 Qwen Max variant.
**Invariant:** ALL FOUR cost fields are zero — not omitted, not null — because the host's cost arithmetic consumes the object shape; quota semantics ride in documentation precisely BECAUSE the wire cost object cannot express them. Model ids and names are unique within a catalog (test-enforced); CN twins keep ids identical and differ only by the `(CN)` display suffix. Casing trap: `MiniMax-M2.5` (:90) is the ONLY non-lowercase id, and its presence test uses `includes("MiniMax")` (:80) where every sibling family test uses lowercase `startsWith` — a naive lowercase normalization would still pass, but id-matching consumers must not assume uniform casing.
**Probe:** `test/models.test.ts`: length 9 (:8-10), required-property sweep (:12-28), every cost field ===0 (:30-40), input vocabulary ⊆ {text,image} (:42-50), positivity of contextWindow/maxTokens (:52-62), vendor-family presence floors ≥4 qwen/:65-67, ≥2 glm/:69-72, ≥1 kimi/:74-77, ≥1 MiniMax via `includes` :79-82, capability presence >0 vision :84-87 and >0 reasoning :89-92, unique ids/names (:94-104), specific-model truth anchors qwen3.5-plus vision+reasoning (:107-112), coder-next contextWindow ≥262144 (:114-118), coder-plus ===1000000 (:120-124), CN parity incl. sorted-id equality and per-field equality (:128-157). Runner BLOCKED this pass (no node_modules); line-pinned reads stand in.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-bailian", semantic_query: ["models", "catalog", "cost"], limit: 8 });
```
Executed live at pin: semantic mode returned only Function nodes (`loginBailianCN` … `refreshBailianToken`, scores ≈ -0.06…-0.11) — the catalog CONSTANTS are Module-level Variables, not Functions, so function-shaped retrieval cannot address them. Retrieve the module node instead:
```ts
await mcp.codebase_memory.search_graph({ project: "pi-bailian", label: "Module", query: "models" });
```
which resolves `pi-bailian.src.models` (src/models.ts :1-187).

## Verdict
Adopt explicit all-zero cost objects with a header comment stating the subscription rationale, plus test-enforced uniqueness and twin parity. Adapt rows/limits to your vendor's real windows. Omit token-price data entirely — inventing prices for a flat-rate plan would corrupt the host's cost ledger.
