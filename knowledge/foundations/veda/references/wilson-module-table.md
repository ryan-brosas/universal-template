<!-- capsule-v2 -->
# Wilson module table — how do you present small-sample win rates next to a Bayesian ranking without overstating them?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** Module groupBy shows single-judge win rates alongside Glicko-2 ratings. Raw win rates lie for tiny samples (1/1 = 100%). How is the second table computed, sorted, and bounded?

## Sort by Wilson lower bound, not raw win rate
**Path/Symbol:** `src/commands/stats.ts` `getModuleWinRates` consumer (:140-160 JSON arm, `displaySingleJudgeWinRates` :198-269 text arm); derivation in `src/stats/store.ts:StatsStore.getModuleWinRates` (:103-145); bound primitive `wilsonLower` in `src/stats/sampling.ts` (:73-86, shared with beta-sampling-kernel).
**Signature:** `getModuleWinRates() → Promise<Map<string, ModuleWinRate>>`; `wilsonLower(wins: number, n: number, z = 1.96) → number`; `ModuleWinRate { moduleKey, wins, appearances, winRate, avgConfidence, lastSeen }`.
**Data Shape:** win rates derive ONLY from v3 stat entries (`if (entry.version !== 3) continue;`); key format `category/moduleId`; every participant gets an appearance, only the winner gets the win + confidence credit.

### Decisive source
```ts
  // Sort by Wilson lower bound (more meaningful than raw win rate for small samples)
  const sorted = [...winRates.values()]
    .map(m => ({ ...m, wilsonLB: wilsonLower(m.wins, m.appearances) }))
    .sort((a, b) => b.wilsonLB - a.wilsonLB || b.appearances - a.appearances)
    .slice(0, options.limit);
```
Derivation (store side):
```ts
      for (const p of v3.participants) {
        const key = `${p.category}/${p.moduleId}`;
        existing.appearances++;
        if (key === winnerKey) {
          existing.wins++;
          existing.totalConfidence += v3.confidence.score;
        }
        if (v3.timestamp > existing.lastSeen) {
          existing.lastSeen = v3.timestamp;
        }
      }
```
**Flow:** `getModuleWinRates` folds v3 entries into per-module {wins, appearances, totalConfidence, lastSeen} — every participant counts an appearance, the winner additionally counts a win and accumulates the judge's confidence score → `avgConfidence = totalConfidence / wins` (0 for winless modules) → the display layer computes `wilsonLB = wilsonLower(wins, appearances)` per row and sorts by it (ties: more appearances first) → text table shows `Win%`, `W/A`, and `≥LB` columns; JSON mode nests `singleJudgeWinRates` beside `glicko2Ratings` in one document.
**Invariant:** ranking and color-coding use the Wilson LOWER bound (95% confidence floor on the true win rate), never the raw rate — a 1/1 module (raw 100%) gets LB ≈ 21% and ranks below a 10/12 module (raw 83%, LB ≈ 65%). The bound is the same primitive the module-selection ladder uses, so display and selection agree on what a small sample means. Winless modules still appear (appearances > 0) with LB 0 — absence of wins is not absence of evidence.
**Probe:** `src/stats/sampling.test.ts` (executed live at pin: 14 pass / 0 fail, 482 expect) pins the Wilson bound table (1/1 → ~0.21, 10/10 → ~0.72); `getModuleWinRates` itself has no dedicated upstream test (grep-verified: 0 hits in tests/) — source-pinned probe: `grep -n "b.wilsonLB - a.wilsonLB" src/commands/stats.ts` → `146:        .sort((a, b) => b.wilsonLB - a.wilsonLB || b.appearances - a.appearances)`.
**Coverage caveat:** the v3-entry fold and the display sort are source-pinned only; the sampling suite covers the bound math.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "getModuleWinRates wilsonLower singleJudgeWinRates ModuleWinRate participants winner confidence", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Wilson-lower-bound sort for any win-rate display and the participants-get-appearances fold (winless modules stay visible). Adapt the z-score and the v3-only version gate to your log schema. Omit avgConfidence if your judges emit no confidence scores.
