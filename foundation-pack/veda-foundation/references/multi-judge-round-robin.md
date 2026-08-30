<!-- capsule-v2 -->
# Round-robin judge assignment — how do you eliminate self-preference bias when each backend judges every candidate except its own?

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** How are judge→candidate assignments built so no judge ever scores a candidate from its own solver backend, and what is the exact coverage expectation?

## Cross-backend exclusion + deterministic shuffle
**Path/Symbol:** `src/core/multi-judge.ts` : `buildJudgeAssignments` (:104-141) + `validateAssignments` (:148-181) + seed helpers `buildShuffleSeed`/:78, `hashString`/:87.
**Signature:** `function buildJudgeAssignments(candidates: CandidateInfo[], promptHash: string, judgeBackendOverride?: string[]): JudgeAssignment[]`.
**Data Shape:** `CandidateInfo = { id, solverBackend, content }`; `JudgeAssignment = { judgeBackend, candidateIds (display order), indexMapping (= shuffled ids), seed }`.

### Decisive source
```ts
// Extract unique solver backends (preserving order)
const solverBackends = [...new Set(candidates.map(c => c.solverBackend))];
const judgeBackends = judgeBackendOverride ?? solverBackends;
for (const judgeBackend of judgeBackends) {
  // Judge evaluates all candidates EXCEPT those from its own backend
  const targetCandidates = candidates.filter(c => c.solverBackend !== judgeBackend);
  if (targetCandidates.length === 0) continue;          // single-backend pool → judge skipped
  const candidateIds = targetCandidates.map(c => c.id);
  const seed = buildShuffleSeed(promptHash, judgeBackend, candidateIds);   // `${promptHash}::${judgeBackend}::${ids.join(',')}`
  const { indexMapping } = shuffleCandidates(candidateIds, seed);
  assignments.push({ judgeBackend,
                     candidateIds: indexMapping.map(origIdx => candidateIds[origIdx]),
                     indexMapping: shuffledCandidateIds, seed });
}
```

**Flow:** unique backends (insertion-ordered) become the judge roster unless overridden → per judge, own-backend candidates filtered OUT → remaining ids deterministically shuffled with a per-(task,judge,pool) seed for position debiasing → assignment stored in DISPLAY order. Coverage contract: N≥2 backends ⇒ every candidate judged exactly N−1 times; N=1 ⇒ zero assignments (`validateAssignments` expects 0 and runMultiJudge throws 'No valid judge assignments'). Validation failures under override only WARN (`console.error`) then proceed.
**Invariant:** exclusion is by SOLVER BACKEND string equality — a judge never sees its own provider's output even when the override re-includes that backend's judge role against its own candidates? No: the filter applies AFTER override resolution, so an overridden judge still skips same-backend candidates. Deterministic seeds make the whole ranking reproducible run-to-run given identical inputs. This module is the legacy round-robin path (unified router owns production today) — port it when you need bias elimination without pairwise expansion.
**Probe:** `tests/core/multi-judge.test.ts:14-40` — 6 candidates over 3 backends → exactly 3 assignments, each holding the OTHER two backends' candidates. Run: `bun test tests/core/multi-judge.test.ts`.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"buildJudgeAssignments cross-provider","limit":5,"detail":"ids"}'
```
→ resolves `veda.src.core.multi-judge.buildJudgeAssignments Function src/core/multi-judge.ts 104-141`.

## Verdict
Adopt the exclusion rule, seed composition, and the N−1 coverage contract verbatim. Adapt CandidateInfo fields to your candidate schema. Omit position-debias shuffling if your judge prompt is position-invariant (but keep determinism).
