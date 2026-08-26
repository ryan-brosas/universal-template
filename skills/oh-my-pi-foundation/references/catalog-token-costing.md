<!-- capsule-v2 -->
# Token cost calculation — how do you price usage across cache tiers and long-context ladders without dropping tokens?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How is a usage record turned into dollars when rates differ by context length and cache-write TTL?

## Threshold-tier rate resolution + TTL-component cache-write pricing with residual fallback
**Path/Symbol:** `packages/catalog/src/models.ts:resolveTokenCost` (:46), `calculateCost` (:58), `cacheWriteCost` (:88); long-context ladder test at `test/long-context-pricing.test.ts`.
**Signature:** `calculateCost(model, usage): Usage["cost"]` (mutates the usage.cost record in place); `calculateUncachedInputCost(cost, promptInputTokens)`.
**Data Shape:** `TokenCost {input, output, cacheRead, cacheWrite, longContext?: {inputThreshold, input, output, cacheRead, cacheWrite}}`; `usage.cttl?: {ephemeral5m?, ephemeral1h?}`; rates are $/MTok.

### Decisive source
```ts
// The tier selector keys on TOTAL prompt input (uncached + cacheRead +
// cacheWrite + orchestration), not just uncached tokens — the context
// LENGTH is what changes the price.
const promptInputTokens =
  usage.input + usage.cacheRead + usage.cacheWrite +
  (orchestration?.input ?? 0) + (orchestration?.cacheRead ?? 0);

// 1h writes bill at 2x base input; derive the multiplier from input rather
// than the stored cacheWrite scalar so legacy entries whose stored scalar
// drifted from 1.25x stay correct. The breakdown is documented to sum to
// usage.cacheWrite but the two come from INDEPENDENT wire fields
// (cache_creation vs cache_creation_input_tokens) — any unattributed
// remainder is priced at the FLAT rate instead of being dropped: a partial
// or stale breakdown must never make write tokens free.
const residual = Math.max(0, usage.cacheWrite - fiveMinute - oneHour);
return rate5m * (fiveMinute + residual) + ((rates.input * 2) / 1000000) * oneHour;
```

**Flow:** resolve active tier (standard vs longContext by threshold) → price each component at its rate over its token count (orchestration sub-usage folded into each side) → cache-write splits 5m/1h/residual → total sums the four.
**Invariant:** (1) unattributed write remainder must still bill (never free); (2) missing cttl ⇒ flat 5-minute-rate pricing for everyone but Anthropic; (3) subscription/alias SKUs share their backing model's tier so cost attribution stays honest (`long-context-pricing.test.ts:39`).
**Probe:** direct `packages/catalog/test/long-context-pricing.test.ts:19` (at-or-below threshold standard rates), `:27` (whole request billed at tier rates once crossed).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "calculateCost cacheWriteCost longContext inputThreshold", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt total-prompt tier selection and the residual-billing cache-write formula; adapt multipliers to your providers' published rates; omit orchestration folding if you have no sub-agent accounting. Coverage caveat: none for the tier ladder; TTL split pinned by source comments (Anthropic-only wire field).
