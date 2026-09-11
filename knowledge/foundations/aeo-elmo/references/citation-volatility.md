<!-- capsule-v2 -->
# Citation volatility — how do you measure whether cited sources are stable?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How do two complementary churn metrics avoid disagreeing about "are my citations moving?"

## Jaccard set distance + Bray–Curtis share distance
**Path/Symbol:** `apps/web/src/lib/visibility-stats.ts:computeVolatility` (L71–114), `bucketByDay` (L46–64), `stabilityScore` (L117–120).
**Signature:** `computeVolatility(daily: DailyDomainCount[]): { setVolatility, weightedVolatility, dayTransitions }` (both null when < 2 days; `dayTransitions` is the reliability gate).
**Data Shape:** input rows `{date:"YYYY-MM-DD", domain, count}` bucket per day (duplicate domains summed, count ≤ 0 dropped, ISO dates sort lexicographically = chronologically). Set distance = `1 − |A∩B|/|A∪B|`; weighted = `1 − Σ_d min(shareCur_d, sharePrev_d)` walking shared domains only.

### Decisive source
```ts
// A prompt with one dominant source every day but a noisy long tail looks
// volatile by set yet stable by volume — weighted is the truer "do the sources
// that carry the answer move?" signal, so it's the one we surface as the
// Stability score.
let overlap = 0;
for (const [d, c] of cur.counts) {
	const prevC = prev.counts.get(d);
	if (prevC === undefined) continue;
	overlap += Math.min(c / cur.total, prevC / prev.total);
}
const weightedDist = 1 - overlap;
```

**Flow:** mean over consecutive-day transitions; both metrics rounded to 3 decimals; Stability score = `round((1 − clamp01(weighted)) × 100)`.
**Invariant:** the two volatilities are deliberately kept distinct and BOTH returned — near-orthogonal signals that answer different questions. Missing-day gaps simply don't form a transition (no imputation here; the SoV trend uses LVCF instead — different question).
**Probe:** `apps/web/src/lib/visibility-stats.test.ts` (pure functions; GREEN in the repo's suite).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "computeVolatility stabilityScore bucketByDay Jaccard Bray", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pair-of-distances contract with the transition-count reliability gate; adapt thresholds/rounding; omit set-volatility from UI only if you also adopt the in-source rationale for why weighted wins.
