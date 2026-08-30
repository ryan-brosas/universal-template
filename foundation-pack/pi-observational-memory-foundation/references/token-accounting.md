<!-- capsule-v2 -->
# Hybrid token accounting — real provider usage with raw-estimate fallback; undefined means "fall back", never zero

**Source:** pi-observational-memory MIT `master@1a50dcd4eff2f2a2f298706499aa7096806d51d4`; Codebase Memory `pi-observational-memory`. **Question:** When do consolidation stages fire, given that estimated tokens and provider-reported context tokens diverge and compaction resets the context mid-session?

## Real growth since anchor (`src/session-ledger/progress.ts`)
**Path/Symbol:** `progress.ts:198-218` (`realTokensSinceAnchor`), `progress.ts:164-185` (`realContextTokensAfterCompaction`, `realContextTokensAtCoverage`), `progress.ts:147-152` (`validAssistantContextTokens`).
**Signature:** `realTokensSinceAnchor(entries, customType | undefined, currentContextTokens): number | undefined`.
**Data Shape:** valid usage = `assistant` messages with `stopReason !== "error" | "aborted"` carrying `usage.totalTokens` or `input+output+cacheRead+cacheWrite`.

### Decisive source
```ts
if (compactionIdx > coverageIdx) {
	const baseline = realContextTokensAfterCompaction(entries, compactionIdx);
	if (baseline === undefined) return undefined;
	const delta = currentContextTokens - baseline;
	return delta >= 0 ? delta : undefined;      // smaller-than-baseline ⇒ basis change ⇒ fall back
}
if (coverageIdx >= 0) {
	const baseline = realContextTokensAtCoverage(entries, coverageIdx);
	if (baseline === undefined) return undefined;
	const delta = currentContextTokens - baseline;
	return delta >= 0 ? delta : undefined;
}
return Math.max(0, currentContextTokens);
```
```ts
// Only usage from an assistant that responded AFTER the compaction is a valid
// post-compaction baseline: pi's own docs state the last assistant usage
// before/at a compaction reflects the PRE-compaction context size.
```

**Flow:** anchor = whichever is later on the branch: last compaction or the stage's coverage marker → find first VALID assistant usage after (compaction) / at-or-before (coverage) the anchor → return `current − baseline`; any unreliability returns `undefined`.
**Invariant:** `undefined` is a FIRST-CLASS answer meaning "caller must use the raw estimate". Measuring from zero would read the whole post-compaction context as growth (over-fire every turn); clamping a negative/stale baseline to 0 would starve the stage forever. The compaction entry's OWN usage is deliberately not a baseline (it belongs to the summary-generation call, pre-compaction scale). Negative delta = accounting basis changed (model/provider switch) ⇒ also `undefined`.

## Raw fallback + threshold gate (`consolidation-trigger.ts`)
**Path/Symbol:** `consolidation-trigger.ts:89-110` (`stageDue`, `anyStageDue`), `consolidation-trigger.ts:83-87` (`realContextTokens`).
**Data Shape:** thresholds from config (`observeAfterTokens` 10k default, `reflectAfterTokens` 20k).

### Decisive source
```ts
function stageDue(entries, runtime, currentTokens, customType, rawEstimateFn, threshold): boolean {
	if (currentTokens !== undefined) {
		const real = realTokensSinceAnchor(entries, customType, currentTokens);
		if (real !== undefined) return real >= threshold;
	}
	// Real delta unmeasurable ... fall back to the raw estimate, which
	// self-limits after coverage and cannot over-fire or starve.
	return rawEstimateFn(entries) >= threshold;
}
```

**Flow:** host `getContextUsage()` supplies real current tokens (guarded for old hosts / unknown values) → prefer the real clock → raw estimate (`estimateEntryTokens` over source entries since coverage, ~4 chars/token) only when real measurement returned `undefined` at either layer.
**Invariant:** The two clocks measure different things (context growth vs. rendered source text) but both SELF-LIMIT once coverage advances, so neither can fire forever. Compaction's own trigger uses ONLY the raw clock (`rawTokensSinceLastCompaction`) because its config counts ledger entries by design.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-observational-memory", query: "realTokensSinceAnchor realContextTokensAfterCompaction contextTokensFromUsage stageDue rawTokensSinceLastCompaction", limit: 10 });
```
(Direct tests: `tests/session-ledger-progress.test.ts` :61 independent clocks, :133 raw-since-compaction robustness; `realTokensSinceAnchor` helpers are below test granularity — pinned to source lines 154-218 which document each `undefined` case.)

## Verdict
Adopt the three-layer ladder (real-since-anchor → raw-estimate → no-fire), `undefined`-means-fall-back semantics, the post-compaction baseline rule, and error/aborted-message exclusion from baselines. Adapt the ~4 chars/token estimator to your tokenizer. Omit nothing behavioral.
