<!-- capsule-v2 -->
# Stats exposure ranking — how do you rank noisy Glicko-2 ratings for display without lying about uncertainty?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A leaderboard over Glicko-2 ratings must not crown a lucky newcomer with a high rating but huge RD. What metric ranks the rows, how are ties broken, and how is uncertainty surfaced to the user?

## Rank by exposure (rating − 2·RD), render uncertainty inline
**Path/Symbol:** `src/commands/stats.ts:handleStats` (:72-194): entry build (:107-119), sort chain (:121-125), `formatRating` (:66-70), uncertainty legend (:191); exposure primitive in `src/stats/glicko2.ts:computeExposure` (:269-271).
**Signature:** `computeExposure(state: RatingState) → number` (= `state.r - 2 * state.rd`); `handleStats(options: StatsOptions) → Promise<void>` with `StatsOptions { groupBy: 'judge'|'model'|'module'|'category'; limit: number; json: boolean; era: EraSelector }`.
**Data Shape:** `RatingEntry { key, displayKey, rating, rd, vol, exposure, games, lastTs? }`; `EraSelector` = `'all' | 'legacy' | 'current' | <explicit era id>`; ratings come from `RatingsStore.getByPrefix(prefix, era)` (era-namespaced keys, stripped for display via `stripEraSuffix`).

### Decisive source
```ts
/**
 * Compute exposure rating (conservative estimate).
 * Used for ranking: rating - 2*RD gives 95% confidence lower bound.
 */
export function computeExposure(state: RatingState): number {
  return state.r - 2 * state.rd;
}
```
```ts
  entries.sort((a, b) => {
    if (Math.abs(a.exposure - b.exposure) > 0.1) return b.exposure - a.exposure;
    if (a.games !== b.games) return b.games - a.games;
    return a.displayKey.localeCompare(b.displayKey);
  });
```
```ts
function formatRating(rating: number, rd: number): string {
  const r = Math.round(rating);
  if (rd > 200) return `${r}?`;  // high uncertainty
  if (rd > 100) return `${r}~`;  // medium uncertainty
  return `${r}`;
}
```
**Flow:** pick the key prefix from `groupBy` (`KEY_PREFIX.JUDGE|MODEL|MODULE|CATEGORY` from derive-matches.ts) → `getByPrefix(prefix, era)` loads only that group's era-namespaced snapshots → strip era suffix + prefix for display → compute exposure per entry → sort exposure-desc (ε=0.1 bucket treats near-equal exposures as ties), then games-desc (more evidence wins ties), then alphabetical → slice to `limit` → render with `?`/`~` uncertainty markers and a legend line (`Rating? = high uncertainty (RD>200), ~ = medium (RD>100)`).
**Invariant:** the ranking metric is the 95% lower bound, never the raw rating — a 1700-rated player with RD 250 ranks below a 1500-rated player with RD 50. The ε-bucket (0.1) prevents float noise from reordering statistically-tied entries; the games tiebreak prefers the better-evidenced row. Era selection changes both the ratings read AND the run count (`pairwiseStore.count()/countByEra(...)`), so the header's run count always matches the rows shown.
**Probe:** `tests/stats/store.test.ts` (executed live at pin: 7 pass / 0 fail) pins the store side (append/readAll/normalization) feeding `getByPrefix`; the ranking chain itself has no dedicated upstream test (grep-verified) — source-pinned probe: `grep -n "b.exposure - a.exposure" src/commands/stats.ts` → `121:    if (Math.abs(a.exposure - b.exposure) > 0.1) return b.exposure - a.exposure;`.
**Coverage caveat:** no test pins the sort chain or formatRating thresholds; both are source-pinned at the cited lines.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "handleStats computeExposure getByPrefix stripEraSuffix exposure ranking formatRating", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exposure-based ranking (rating − 2·RD) with the ε-bucket → games → name tiebreak chain and inline uncertainty markers. Adapt the ε value, the RD thresholds (200/100), and the color bands (1600/1450/1350) to your rating scale. Omit the era plumbing if your store has no learned-state rotation.
