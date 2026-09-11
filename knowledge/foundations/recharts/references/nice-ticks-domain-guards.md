<!-- capsule-v2 -->
# getNiceTickValues — what are the entry guards, degenerate domains, and reversal semantics?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** What must the public tick generator return for infinite, single-value, and reversed (min>max) domains, and how do ticks extend past the domain?

## Domain-extension tick generator
**Path/Symbol:** `src/util/scale/getNiceTickValues.ts:getNiceTickValues` (:232-263).
**Signature:** `getNiceTickValues([min, max]: NumberDomain, tickCount = 6, allowDecimals = true, niceTicksMode: NiceTicksAlgorithm = 'auto') => number[]`.
**Data Shape:** Domain tuple; count floor-lifted via `Math.max(tickCount, 2)`; returns ascending-or-descending numeric array possibly exceeding the domain on both ends.

### Decisive source
```ts
const count = Math.max(tickCount, 2);
const [cormin, cormax] = getValidInterval([min, max]);
if (cormin === -Infinity || cormax === Infinity) {
  const values =
    cormax === Infinity
      ? [cormin, ...Array(tickCount - 1).fill(Infinity)]
      : [...Array(tickCount - 1).fill(-Infinity), cormax];
  return min > max ? values.reverse() : values;
}
if (cormin === cormax) {
  return getTickOfSingleValue(cormin, tickCount, allowDecimals);
}
const stepFn = niceTicksMode === 'snap125' ? getSnap125Step : getAdaptiveStep;
const { step, tickMin, tickMax } = calculateStep(cormin, cormax, count, allowDecimals, 0, stepFn);
const values = rangeStep(tickMin, tickMax.add(new Decimal(0.1).mul(step)), step);
return min > max ? values.reverse() : values;
```

**Flow:** normalize order (`getValidInterval` swaps if needed) → infinite-end guard fills the unbounded side with ±Infinity sentinels (keeps array length = tickCount) → equal endpoints delegate to the single-value generator → pick `StepFunction` by mode → compute anchored boundaries → walk with `rangeStep` whose end is padded by **0.1×step** so the top tick (inclusive in Decimal terms) survives the half-open loop → reverse iff the ORIGINAL input was descending.
**Invariant:** Output always contains exactly `tickCount` entries except where noted; the 0.1·step pad is the subtle part ported wrong most often — without it the last tick vanishes because `rangeStep` excludes its end.
**Probe:** `test/util/scale/getNiceTickValues.spec.ts` ("should return correct ticks with Infinity values [-100, Infinity, 5]" pins `[-100, Inf, Inf, Inf, Inf]`; "should return correct ticks with min is bigger than max & has odd ticks" pins `[67,5],5 → [80,60,40,20,0]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "getNiceTickValues", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt all four guards verbatim; adapt only the mode dispatch if you lack snap125; omit nothing. Upstream spec pins every degenerate class including both pure-±Infinity domains and mixed.
