<!-- capsule-v2 -->
# Rating derivation — one vote fans out to four entity ladders; judges scored against consensus

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How do I turn raw pairwise votes into per-entity match lists suitable for a rating system (Glicko-2), across models, modules, categories AND judges?

## Prefixed keys + self-match skip + consensus-referenced judge scoring
**Path/Symbol:** `src/stats/derive-matches.ts:deriveModelMatches/deriveModuleMatches/deriveCategoryMatches` (:60–177), `deriveJudgeMatches` (:188–292), `mergeMatches` (:315–327).
**Signature:** `function derive*(entry: AnyPairwiseStatEntry): MatchesByKey` (Map keyed by prefixed entity key → `{opponentKey, score}[]`); scores ∈ {0, 0.5, 1}.
**Data Shape:** `KEY_PREFIX = { JUDGE:'judge:', MODEL:'solver:', MODULE:'module:', CATEGORY:'category:' }`; candidate metadata carries solverBackend/solverModel/category/moduleId; votes carry pairId/outcome(A|B|tie) and judgeBackend/judgeModel.

### Decisive source
```ts
// Judge scoring is REFERENCED AGAINST CONSENSUS, not head-to-head preference:
// - Judge pairs are matched head-to-head
// - Judge whose vote matches consensus wins; other loses
// - If both match or both differ from consensus: draw
// - If verdict is tie/split: draw for all
const isTieOrSplit = verdict === 'tie' || verdict === 'split';
if (isTieOrSplit) { score1 = 0.5; score2 = 0.5; }
else {
  const v1Correct = v1.outcome === verdict;
  const v2Correct = v2.outcome === verdict;
  if (v1Correct && !v2Correct)      { score1 = 1; score2 = 0; }
  else if (!v1Correct && v2Correct) { score1 = 0; score2 = 1; }
  else { score1 = 0.5; score2 = 0.5; } // both correct or both wrong: draw
}
```

**Flow:** one vote produces TWO mirrored match rows (A's list gets {vs B, scoreA}, B's list gets {vs A, scoreB}) in every ladder → identical-entity votes are SKIPPED (`keyA === keyB`) so a model never plays itself → verdict lookup prefers stored `pairResults`, else derives majority from votes with strict-majority (ties of counts ⇒ `'split'` ⇒ all-draw) → judge pairs formed from all vote combinations within a pair.
**Invariant:** Mirrored insertion (both sides get exactly one row per vote) preserves zero-sum rating math; dropping one side silently deflates every rating. Self-match skip must run BEFORE row creation. The consensus-reference (not co-vote agreement) is what makes judge ratings comparable across different candidate pairs.
**Probe:** `tests/stats/derive-matches.test.ts` (:15–230) — `skips self-matches for same model`, `draws when verdict is split`, `winner when one judge matches consensus`, `derives verdict from votes when pairResults missing`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "deriveJudgeMatches deriveModelMatches KEY_PREFIX", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-ladder fan-out, mirrored rows, self-match skip, and consensus-referenced judge scoring as a unit — they form the soundness contract feeding Glicko-2. Adapt prefixes/entity axes to your leaderboard's dimensions. Omit mergeMatches if your host has no cross-source aggregation.
