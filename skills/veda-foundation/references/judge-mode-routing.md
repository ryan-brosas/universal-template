<!-- capsule-v2 -->
# Unified judge mode routing — when do requested judge modes silently degrade to single, and how do three modes return one result shape?

**Source:** veda MIT `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`; Codebase Memory `veda`. **Question:** How do you support single/multi/pairwise judging behind one entry point without leaking mode differences into consumers?

## runUnifiedJudge adapter trio
**Path/Symbol:** `src/core/judge-unified.ts:runUnifiedJudge` (:172-236) + adapters (:241-403 single, :304-403 multi, :408-545 pairwise) + capability predicates `canUseMultiJudge/canUsePairwiseJudge/getEffectiveJudgeMode` (:550-582).
**Signature:** `runUnifiedJudge(args: RunUnifiedJudgeArgs): Promise<UnifiedJudgeResult>`; `getEffectiveJudgeMode(requested: JudgeMode, candidateInfos: CandidateInfo[]): JudgeMode`.
**Data Shape:** `UnifiedJudgeResult {mode, selected, selectedIndex, selectedCandidateId?, confidence, confidenceLevel, winMargin, reasoning?, indexMapping, judges[], aggregation?, usage, sessionId?, hadFailures?, winnerRationales?, pairResults?, pairwiseVotes?}`.

### Decisive source
```ts
if (mode === 'pairwise' && candidateInfos && uniqueBackends > 1) {
  // Pairwise requires 2+ backends for cross-provider judging
  return runPairwiseJudgeAdapter({...});
} else if (mode === 'multi' && uniqueBackends > 1 && candidateInfos) {
  return runMultiJudgeAdapter({...});
} else {
  // Single-judge fallback
  return runSingleJudgeAdapter({...});
}
```

**Flow:** capability check = count DISTINCT `solverBackend` values on candidates (>1 required for multi/pairwise; <2 candidates kills pairwise) → each adapter normalizes into the SAME UnifiedJudgeResult: single sets winMargin=1.0 (no runner-up exists); multi aggregates via `normalized_rank_average`; pairwise via `pairwise_copeland` with per-pair results and flattened votes for stats → winner rationales extracted only from judges who ranked the winner #1 (multi) or voted for it (pairwise, one rationale per judge with pair context).
**Invariant:** Mode degradation is SILENT by design (requested 'pairwise' on one backend → 'single') — consumers must read `result.mode`, never assume the request was honored; `winMargin` is a verification trigger input so single-mode's constant 1.0 is load-bearing; synthesized reasoning strings (avg rank / Copeland summary) exist because aggregation has no native LLM rationale.
**Probe:** `tests/core/judge-unified.test.ts` (13 tests: canUseMultiJudge ×3, getEffectiveJudgeMode ×6 incl. both fallbacks, canUsePairwiseJudge ×3) — EXECUTED this pass: 12 pass / 0 fail at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "getEffectiveJudgeMode runUnifiedJudge", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt capability-gated mode routing with a normalized result envelope for any ensemble-evaluation system. Adapt the confidence vocabulary (`high|medium|low` + numeric scores). Omit legacy multi-ranking if starting fresh — upstream itself calls it "(ranking, legacy)" vs recommended pairwise.
