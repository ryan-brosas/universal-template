<!-- capsule-v2 -->
# Index-set planner — how do N validated index candidates collapse to ONE recommended set with explicit rejections?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How are candidates classified, deduped by canonical field set, and ranked into a final recommendation with full audit of what was rejected and why?

## Five-way classifier + canonical-key grouping + four-factor ranking
**Path/Symbol:** `packages/v2/table-query-ops/src/indexSetPlanner.ts` whole (235L): `classifyCandidate` (:101-144), defaults (:70-72: minCostImprovementPct 20, minAbsoluteCostImprovement 1, lowCostBeforeThreshold 5), `canonicalFieldSetKey` (:80-83: `[indexKind, fields.map(fieldIdentity).filter(Boolean).sort().join('|')].join(':')` — ORDER-INSENSITIVE field sets), `compareCandidates` (:159-176), `planRecommendedIndexSet` (:178-235).
**Signature:** `planRecommendedIndexSet(candidates, options?) → {recommendedIndexSet, rejectedCandidates}`.
**Data Shape:** nextAction vocabulary: `ready_for_confirmation | no_index_change | candidate_not_recommended | needs_plan_validation | manual_investigation`; rejection reasons carry `coveredByCandidateId` when deduped.

### Decisive source
```ts
if (candidate.explainStatus !== 'validated') return
  candidate.explainStatus === 'failed' ? {nextAction:'manual_investigation', reason:'plan_validation_failed'}
                                       : {nextAction:'needs_plan_validation', reason:'plan_validation_missing'};
if (candidate.plannerUsedIndex !== true) return {nextAction:'candidate_not_recommended', reason:'planner_did_not_use_index'};
if (delta >= 0) return {nextAction:'candidate_not_recommended', reason:'cost_not_improved'};
if (before <= lowCostBeforeThreshold && absoluteImprovement < minAbsoluteCostImprovement)
  return {nextAction:'manual_investigation', reason:'low_absolute_cost_improvement'};   // cheap plans: absolute floor
if (relativeImprovement < options.minCostImprovementPct)
  return {nextAction:'manual_investigation', reason:'low_relative_cost_improvement'};
return { nextAction: 'ready_for_confirmation' };
```
Ranking: sourceCount DESC → absolute-improvement DESC → relative-improvement DESC → fewer-fields → candidateId ASC (total order, deterministic).

**Flow:** classify every candidate → survivors grouped by canonical key (same kind+field SET in any order = same index intent; spec pins "keeps one final composite index … different order") → per group sort + winner takes all, losers rejected as `covered_by_better_index_candidate` → recommended sorted by the same comparator.
**Invariant:** The dual-threshold gate (absolute for cheap plans, percentage otherwise) prevents both "saved 0.3 cost units on a cost-4 plan" noise AND percentage-only bias against big plans; plannerUsedIndex must be EXPLICITLY true (`!== true` rejects undefined) so absent evidence never passes. Every rejected candidate keeps its full payload + machine-readable reason — the audit trail is the product.
**Probe:** `indexSetPlanner.spec.ts:30/:73/:94`.
**Coverage caveat:** none — pure function, three direct specs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "planRecommendedIndexSet classifyCandidate canonicalFieldSetKey", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt classification→group→rank pipeline with total-order tiebreakers and dual thresholds; adapt constants; keep rejection records first-class — downstream confirm UIs depend on them.
