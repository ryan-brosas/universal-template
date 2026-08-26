<!-- capsule-v2 -->
# Multi-point cache strategy — how do you place a BUDGETED set of cache points in a growing conversation without invalidating the previous request's cache?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When the backend allows only N cache points (Bedrock `cachePoint` blocks) and each costs a minimum token count, where do they go this turn — and how do you decide between keeping last turn's placements and re-allocating?

## Placements are CARRIED across requests; prefix stability beats tail coverage; reallocation needs +20% benefit
**Path/Symbol:** `src/api/transform/cache-strategy/multi-point-strategy.ts` (`MultiPointStrategy.determineOptimalCachePoints` :14-61; `determineMessageCachePoints(minTokensPerPoint, remainingCachePoints)` :63-246; combine gate `requiredPercentageIncrease = 1.2` :158-159; `findOptimalPlacementForRange` :248-305; `formatWithoutCachePoints` :307-320) + base machinery `src/api/transform/cache-strategy/base-strategy.ts` (`class CacheStrategy` :5; heuristic tokenizer `calculateSystemTokens` :30-52 / `estimateTokenCount` :100-146 — words×1.3 + punctuation×0.3 + newlines×0.5, images flat 300; threshold gate `meetsMinTokenThreshold` :87-92 returns FALSE when model lacks `minTokensPerCachePoint`; `applyCachePoints` :148-163 pushes `{cachePoint:{type:"default"}}` blocks at placement indices).
**Signature:** `determineOptimalCachePoints(): CacheResult` where `CacheResult = { system: SystemContentBlock[], messages: Message[], messageCachePointPlacements?: CachePointPlacement[] }`; caller contract: pass `messageCachePointPlacements` back next turn as `config.previousCachePointPlacements`.
**Data Shape:** `CachePointPlacement = { index: number (message idx), type: "system"|"message", tokensCovered: number }`; per-conversation state lives in the PROVIDER (`bedrock.ts:1163 previousCachePointPlacements: {[conversationId]: any[]}`), not the strategy.

### Decisive source
```ts
if (!this.config.usePromptCache || messages.length === 0) return formatWithoutCachePoints()
// system plane: mark system ONLY if cachableFields includes "system" AND meetsMinTokenThreshold(systemTokenCount)
if (supportsSystemCache && systemPrompt && meetsMinTokenThreshold(this.systemTokenCount)) {
    systemBlocks.push(createCachePoint()); remainingCachePoints--      // SIBLING block after {text}
}
const placements = determineMessageCachePoints(minTokensPerPoint, remainingCachePoints)
cacheResult.messageCachePointPlacements = placements   // caller MUST feed these back next turn

// inside determineMessageCachePoints:
if (previousPlacements.length === 0) { /* greedy first-fill */ }
else if (newMessagesTokens >= minTokensPerPoint) {
    if (remainingCachePoints > previousPlacements.length) { keep all + add one }
    else {
        // find consecutive pair with SMALLEST combined token gap ...
        const requiredTokenThreshold = smallestGap * 1.2   // +20% benefit REQUIRED to reallocate
        if (newMessagesTokens >= requiredTokenThreshold) { /* merge that pair, free slot → new tail point */ }
        else { keep all previous placements, NO new point }  // ← prefix stability WINS
    }
} else { keep all previous placements }                        // ← and here
// findOptimalPlacementForRange scans BACKWARD for the LAST user message in range;
// null when startIndex >= endIndex OR tokensCovered < minTokensPerPoint
```
The load-bearing invariant: a cache point only pays off if the prefix it covers is byte-identical to what was cached before. So stale placements that still fit are KEPT even when a fresh tail allocation would cover more tokens today, and merging two old points requires new traffic ≥ smallest adjacent gap × 1.2 — an explicit anti-thrash hysteresis. Placement anchor is always the LAST USER MESSAGE of a range (caching everything up to it). Note the marker duality vs the Anthropic-native twin (`anthropic-cache-breakpoints.md`): Bedrock inserts a SEPARATE sibling `{cachePoint:{type:"default"}}` block; Anthropic sets `cache_control` ON the text part.
**Flow:** disabled/empty → no-op formatting → system eligibility check (capability + token floor) → first turn: greedy fill from index 0, each point anchored at its range's last user message with a token-floor guard → later turns: keep-all-when-cheap, add-tail-when-budget-allows, merge-smallest-gap-only-with-+20%-benefit → apply placements as sibling blocks → hand placements back to the provider for the next round trip.
**Invariant:** Placement history is per-conversation caller-owned state — the strategy itself is stateless between calls; total points never exceed `maxCachePoints` (system point decrements the budget); every emitted point covers ≥ `minTokensPerCachePoint` estimated tokens or is dropped (null from the range search); token estimates come from a deterministic word/punct/newline heuristic, never a tokenizer call.
**Probe:** `src/api/transform/cache-strategy/__tests__/cache-strategy.spec.ts` — :61/:70/:77 MultiPoint selected even when caching unsupported/disabled/maxCachePoints=1, :129/:156 system block added when enabled-and-long-enough / model-info-gated, :179 no system block under token floor, :195/:212/:227 empty-messages & caching-disabled negatives, :359/:386/:427 AwsBedrockHandler integration selection.
**Coverage caveat:** heuristic tokenizer constants (1.3/0.3/0.5/image-300) verified against source at this pin; the spec pins strategy selection and system-block gating but does NOT assert specific message-index placements for the reuse/merge branches — those branches are source-read only (no direct behavioral test at this HEAD).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "MultiPointStrategy determineOptimalCachePoints findOptimalPlacementForRange previousCachePointPlacements", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the carried-placement protocol (placements returned to caller, fed back next turn) plus the keep-stale-prefix rule and the ×1.2 reallocation hysteresis for ANY budgeted cache-point backend. Adapt the block vocabulary (`cachePoint` vs `cache_control`) and the token estimator (swap the heuristic for a real tokenizer when billing accuracy matters). Omitting the previous-placements feedback loop silently converts the design into naive tail-caching that re-bills the whole prefix on every turn.
