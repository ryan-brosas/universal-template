<!-- capsule-v2 -->
# Ranking-repair ladder — how do you salvage a judge's malformed ranking instead of discarding the whole pool?

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** When an LLM judge returns duplicate, missing, or gapped rankings over N candidates, what is the deterministic repair order that still yields a complete 1..N permutation?

## Parse → dedupe → backfill → renormalize
**Path/Symbol:** `src/core/multi-judge.ts` : `parseRankingResponse` (:233-320); strict format spec in `MULTI_JUDGE_SYSTEM_PROMPT` (:26-70).
**Signature:** `function parseRankingResponse(text: string, indexMapping: string[]): { rankings: CandidateRanking[]; consensusAnalysis?: string; repaired: boolean }`.
**Data Shape:** `<rank position="N" confidence="high|medium|low"><candidate>D</candidate><reasoning>…</reasoning></rank>` entries; D is a DISPLAY index (1-based) mapped through indexMapping to candidate ids.

### Decisive source
```ts
// Handle duplicates: first occurrence wins
if (seenCandidates.has(displayIdx)) { repaired = true; continue; }
// Handle duplicate ranks: skip
if (seenRanks.has(position))       { repaired = true; continue; }
...
// Attempt repair: add missing candidates at the bottom
if (rankings.length < poolSize) {
    repaired = true;
    let nextRank = Math.max(...seenRanks, 0) + 1;
    for (let displayIdx = 1; displayIdx <= poolSize; displayIdx++) {
      if (!seenCandidates.has(displayIdx)) {
        const candidateId = indexMapping[displayIdx - 1];
        if (candidateId) rankings.push({ candidateId, rank: nextRank++, confidence: 'low',
            reasoning: '(Ranking repaired: candidate was missing from judge response)' });
      }
    }
}
// Re-normalize ranks to be 1..n if there are gaps
rankings.sort((a, b) => a.rank - b.rank);
rankings.forEach((r, i) => { if (r.rank !== i + 1) { r.rank = i + 1; repaired = true; } });
```

**Flow:** extract `<consensus_analysis>` + `<rankings>` blocks (case-insensitive) → per-entry regex accepts optional reasoning → out-of-range display indexes dropped silently → duplicate CANDIDATE (first wins) and duplicate POSITION both skipped with `repaired=true` → missing candidates backfilled at the bottom with confidence 'low' and a self-describing repair reason → final sort + gap-closing renormalization guarantees ranks are exactly 1..poolSize. Caller (`executeSingleJudgePool`) still THROWS if the count mismatches after all repair — repair fixes quality, not absence.
**Invariant:** output is always a complete permutation of the pool or an exception — never partial; `repaired` must surface to consumers because repaired entries carry manufactured low confidence that feeds downstream confidence aggregation. Backfill preserves display-order determinism (ascending displayIdx), so two runs on identical input produce identical repairs.
**Probe:** `tests/core/multi-judge.test.ts` — 'should handle duplicate candidates (first wins)' plus parse/repair describe block pins. Run: `bun test tests/core/multi-judge.test.ts`.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"parseRankingResponse repaired","limit":5,"detail":"ids"}'
```
→ resolves `veda.src.core.multi-judge.parseRankingResponse Function src/core/multi-judge.ts`.

## Verdict
Adopt the four-stage repair order verbatim (dedupe-first-wins → position-dedupe → ascending backfill → gap renormalize) and the always-permutation-or-throw contract. Adapt the regex to your judge's markup. Omit consensus-analysis extraction if unused.
