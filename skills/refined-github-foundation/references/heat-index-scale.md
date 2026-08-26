<!-- capsule-v2 -->
# heat-index-scale — how do you map arbitrary value ranges onto a fixed 10-step heat-color scale like GitHub's activity graphs?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the exact min/max→color-bucket computation, including its clamping and inversion rules?

## Closure-based heat index factory
**Path/Symbol:** `source/helpers/math.ts:createHeatIndexFunction` (:107–122); core `inverseLinearInterpolation` (:88–94); sibling `randomArrayItem` (:124–126).
**Signature:** `createHeatIndexFunction(numbers: number[]): (value: number) => number`; returns index `1..10` where **1 = hottest** (GitHub's L1..L10 classes).
**Data Shape:** Factory takes the full population once (min/max derived from it); returned function maps any single value.

### Decisive source
```ts
function inverseLinearInterpolation(min: number, max: number, value: number): number {
	if (min === max) return 0;               // degenerate range guard
	return (value - min) / (max - min);
}
export function createHeatIndexFunction(numbers: number[]): (value: number) => number {
	const steps = 10; // GH has 10 heat colors
	const min = Math.min(...numbers);
	const max = Math.max(...numbers);
	return (value: number) => {
		const interp = Math.max(0, Math.min(1,
			inverseLinearInterpolation(min, max, value)));   // clamp to [0,1]
		const floored = Math.floor(interp * steps);          // [0..10)
		return Math.max(1, steps - floored);                 // inverted: high value → low index
	};
}
```

**Flow:** normalize value into [0,1] against the population's range (clamped both ends so outliers don't overflow buckets) → multiply by 10 and floor → INVERT (`steps - floored`) because GitHub's heat ladder counts DOWN from hottest (L1) → floor at 1 so the coldest bucket is reachable but 0 never is.
**Invariant:** Three guards compose: `min===max ⇒ 0` (flat data → uniform hottest), double-clamp before flooring, and post-inversion `Math.max(1, …)` — dropping any one yields an off-by-one bucket or NaN on constant ranges. Index direction (1=hottest) is a HOST convention and must match the CSS class mapping.
**Probe:** No direct unit test file for math.ts (pure functions; consumers exercise via heat-map features). Caveat recorded — deterministic function, contract pinned by source read.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "createHeatIndexFunction", limit: 10 });
// → refined-github.source.helpers.math.createHeatIndexFunction Function source/helpers/math.ts
```

## Verdict
Adopt verbatim for any binned-intensity visualization (contribution graphs, activity heatmaps, severity scales): population-scoped normalization + clamp + floor + inverted bucketing. Adapt step count (10 → your palette size) and index polarity to your CSS ladder; keep all three numeric guards exactly.
