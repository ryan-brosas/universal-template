<!-- capsule-v2 -->
# calculateStep — how are tick boundaries anchored so 0 is always a tick and the count fits?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** How does recharts place the first/last tick around a chosen middle anchor, and how does it converge when the nice step makes the requested count impossible?

## Middle-anchored step search
**Path/Symbol:** `src/util/scale/getNiceTickValues.ts:calculateStep` (:159-219).
**Signature:** `calculateStep(min, max, tickCount, allowDecimals, correctionFactor = 0, stepFn = getAdaptiveStep) => { step: Decimal; tickMin: Decimal; tickMax: Decimal }`.
**Data Shape:** Numeric domain endpoints (finite required — callers pre-handle ±Infinity); output triple where ticks run `tickMin … tickMax` inclusive at spacing `step`.

### Decisive source
```ts
// dirty hack (for recharts' test)
if (!Number.isFinite((max - min) / (tickCount - 1))) {
  return { step: new Decimal(0), tickMin: new Decimal(0), tickMax: new Decimal(0) };
}
// An interval with 0 strictly inside it gets a tick at 0 plus one on either side of it,
// so fewer than three ticks never fit and the correction below would recurse forever.
const count = min < 0 && max > 0 ? Math.max(tickCount, 3) : tickCount;
const step = stepFn(new Decimal(max).sub(min).div(count - 1), allowDecimals, correctionFactor);
// When 0 is inside the interval, 0 should be a tick
if (min <= 0 && max >= 0) {
  middle = new Decimal(0);
} else {
  middle = new Decimal(min).add(max).div(2);
  // minus modulo value
  middle = middle.sub(new Decimal(middle).mod(step));
}
let belowCount = Math.ceil(middle.sub(min).div(step).toNumber());
let upCount = Math.ceil(new Decimal(max).sub(middle).div(step).toNumber());
const scaleCount = belowCount + upCount + 1;
if (scaleCount > count) {
  // When more ticks need to cover the interval, step should be bigger.
  return calculateStep(min, max, count, allowDecimals, correctionFactor + 1, stepFn);
}
if (scaleCount < count) {
  upCount = max > 0 ? upCount + (count - scaleCount) : upCount;
  belowCount = max > 0 ? belowCount : belowCount + (count - scaleCount);
}
return { step, tickMin: middle.sub(new Decimal(belowCount).mul(step)), tickMax: middle.add(new Decimal(upCount).mul(step)) };
```

**Flow:** degenerate guard → lift zero-straddling requests to ≥3 ticks (prevents infinite recursion because a straddling interval always needs the 0 tick plus neighbors) → derive rough step from `(max-min)/(count-1)` → round via injected `stepFn` → anchor `middle` at 0 when the domain contains it (else snap midpoint DOWN to a step multiple) → ceil-count ticks needed below/above → recurse with `correctionFactor+1` if too many, else pad the side away from zero toward max/min to hit the exact count.
**Invariant:** Ticks may extend OUTSIDE `[min,max]` — that is the point (nicer numbers); the surplus-tick pad goes to the positive side when `max > 0`, else the negative side. The recursion always terminates because each level raises the correction factor, monotonically raising the step.
**Probe:** `test/util/scale/getNiceTickValues.spec.ts` ("should use 3 ticks when the interval contains 0 but fewer are requested": `calculateStep(-100, 100, 2, true, 0)` yields `{step:100, tickMin:-100, tickMax:100}`; also pins `[100,200]×5 → {25,100,200}`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "calculateStep", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole convergence ladder including the ≥3 lift for zero-straddling domains (v3 regression fix; skipping it hangs your port); adapt the anchor rule only if your charts forbid domain extension (then use `getTickValuesFixedDomain` instead); omit nothing. Upstream tests pin both the straddle case and the normal case.
