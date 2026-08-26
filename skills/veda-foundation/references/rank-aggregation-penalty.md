<!-- capsule-v2 -->
# Rank aggregation & failure-penalty — how do N judges' rankings collapse into one winner with an honest confidence number?

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** What is the exact sort/tiebreak chain, how do failed judge pools discount confidence, and what does winMargin mean when there is no runner-up?

## Borda-flavored aggregation kernel
**Path/Symbol:** `src/core/multi-judge.ts` : `processJudgeResults` (:492-514), `applyConfidencePenalty` (:517-530), `aggregateJudgeResults` (:533-648); tier/score constants in `src/core/multi-judge-types.ts` :119-137.
**Signature:** `function aggregateJudgeResults(judgeResults: JudgePoolResult[], candidates: CandidateInfo[], penalty: ConfidencePenaltyTier): MultiJudgeResult`.
**Data Shape:** per candidate → `RankEntry[] {judgeBackend, rank, poolSize, normalizedRank, confidence}`; normalizedRank = `(rank−1)/(poolSize−1)` ∈ [0,1], 0=best; `CONFIDENCE_SCORES = {high:0.9, medium:0.6, low:0.3}`.

### Decisive source
```ts
scores.sort((a, b) => {
    if (Math.abs(a.avgNormalizedRank - b.avgNormalizedRank) > 0.001) return a.avgNormalizedRank - b.avgNormalizedRank;
    if (a.judgeCount !== b.judgeCount)          return b.judgeCount - a.judgeCount;  // more coverage wins
    if (a.rawRankSum !== b.rawRankSum)          return a.rawRankSum - b.rawRankSum;  // Borda
    if (Math.abs(a.confidenceScore - b.confidenceScore) > 0.001) return b.confidenceScore - a.confidenceScore;
    return a.candidateId.localeCompare(b.candidateId);                                // determinism
});
const winMargin = runnerUp ? runnerUp.avgNormalizedRank - winner.avgNormalizedRank : 1.0;

// penalty tiers: NONE→score; SOME_FAILURES (failureCount>0)→score*0.85;
// MOST_FAILURES (failureRatio>=0.5)→score*0.65   (applyConfidencePenalty)
```

**Flow:** failed pools dropped FIRST (`processJudgeResults`) and their ratio picks the penalty tier (≥50% failures → MOST_FAILURES ×0.65; any failure → SOME_FAILURES ×0.85) → per-candidate rank entries collected across judges → five-key sort (avg normalized rank ε-compared at 0.001, then judgeCount DESC, rawRankSum ASC, confidenceScore DESC, id ASC for determinism) → winner + runner-up produce winMargin (single-candidate pools report the sentinel 1.0 — same value judge-unified's verify gate treats as a non-trigger, so the two planes compose) → winner's aggregated confidence penalized by the failure tier and re-mapped to a level via `scoreToLevel` (high ≥0.75, medium ≥0.45).
**Invariant:** unjudged candidates get avgNormalizedRank 1.0 + confidence 0.3 but can still win only via tiebreak pathologies — never crash on missing entries; ε-comparison at 0.001 prevents float noise from overriding the judge-count tiebreak; the penalty multiplies ONLY the winner's confidence score, never the ranking order.
**Probe:** `tests/core/multi-judge.test.ts` — 'should select winner with lowest average normalized rank', 'should apply confidence penalty', 'should use tiebreakers when ranks are equal'. Run: `bun test tests/core/multi-judge.test.ts`.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"aggregateJudgeResults winMargin","limit":5,"detail":"ids"}'
```
→ resolves `veda.src.core.multi-judge.aggregateJudgeResults Function src/core/multi-judge.ts`.

## Verdict
Adopt the sort chain, ε-comparisons, penalty tiers, and the winMargin=1.0 single-candidate sentinel verbatim. Adapt score constants if your downstream gates use different thresholds. Omit usage folding (mechanical sum) — nothing subtle there.
