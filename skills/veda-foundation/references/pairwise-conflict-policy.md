<!-- capsule-v2 -->
# Pairwise judge conflict-of-interest — how do you generate head-to-head pairs and aggregate votes so no provider grades its own work?

**Source:** veda MIT `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`; Codebase Memory `veda`. **Question:** How are candidate pairs generated, judges assigned, and winners elected when the judges ARE the solver backends?

## generatePairs (Policy B) → assignments → Copeland
**Path/Symbol:** `src/core/pairwise-judge.ts:generatePairs` (:83-119), `validatePairCoverage` (:121-131), `buildPairwiseAssignments` (:154-…), `computeCopelandScores` (:376-437).
**Signature:** `generatePairs(candidates: CandidateInfo[], judgeBackends: string[]): CandidatePair[]`; `computeCopelandScores(candidates, pairResults): PairwiseScore[]`.
**Data Shape:** `CandidatePair {id: "a:b", candidateA/B, backendA/B, isSameBackend, eligibleJudges}`; pair id is LEXICALLY ordered by candidate id so "a:b" vs "b:a" can never duplicate; `PairwiseScore {wins, losses, ties, copelandScore, headToHead, totalPairs}`.

### Decisive source
```ts
// Ensure consistent ordering (lexical by ID)
const [candA, candB] = a.id < b.id ? [a, b] : [b, a];
const isSameBackend = candA.solverBackend === candB.solverBackend;
// Policy B: eligible unless produced BOTH candidates
// Same-backend: exclude that backend
// Cross-backend: all judges eligible
const eligibleJudges = isSameBackend
  ? judgeBackends.filter(jb => jb !== candA.solverBackend)
  : judgeBackends;
```

**Flow:** all C(k,2) pairs generated with lexical id ordering → coverage validated (every pair needs ≥1 eligible judge — fails loud on 2-solver same-backend configs) → each judge receives only its eligible pairs, seeded deterministically from promptHash (`hashString`) → per-pair verdicts A/B/tie/split aggregated by majority of votes into `consensusWinner` + `agreementRate` → Copeland score = wins − losses, sorted Copeland DESC → wins DESC → losses ASC → id ASC.
**Invariant:** A judge who produced BOTH candidates of a pair must be excluded (Policy B); deterministic seeding makes judge assignment reproducible for identical inputs; the 4-way tiebreak chain matters because Copeland ties are common at small k; 'split' (no consensus) counts as ties for BOTH candidates, never a win.
**Probe:** `tests/core/pairwise-judge.test.ts` (:16 C(k,2) pair count + lexical ids, :40-60 Policy B eligibility both branches, :93 validatePairCoverage, :325 computeCopelandScores, :452 "2-backend scenario (the key fix)") — EXECUTED this pass: pass / 0 fail at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "generatePairs eligibleJudges computeCopelandScores", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt Policy B eligibility + lexical pair ids + full tiebreak chain for any self-grading ensemble. Adapt vote vocabulary. Omit deterministic hash-seeding only if you accept nondeterministic assignments.
