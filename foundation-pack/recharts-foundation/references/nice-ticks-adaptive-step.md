<!-- capsule-v2 -->
# getAdaptiveStep — how is a rough tick step rounded into a "reasonable" number?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** When an axis needs N evenly spaced ticks, what exact rounding turns the raw step `(max-min)/(count-1)` into a human-friendly step, and why do the scale factors differ between magnitudes?

## Default step rounding ladder
**Path/Symbol:** `src/util/scale/getNiceTickValues.ts:getAdaptiveStep` (:37-56).
**Signature:** `getAdaptiveStep(roughStep: Decimal, allowDecimals: boolean, correctionFactor: number) => Decimal`.
**Data Shape:** Inputs: arbitrary-precision Decimal step (may be tiny/huge), decimals flag, integer correction factor (recursion depth from `calculateStep`). Output: Decimal ≥ 0; exactly `Decimal(0)` when `roughStep.lte(0)`.

### Decisive source
```ts
const digitCount = getDigitCount(roughStep.toNumber());
// The ratio between the rough step and the smallest number which has a bigger
// order of magnitudes than the rough step
const digitCountValue = new Decimal(10).pow(digitCount);
const stepRatio = roughStep.div(digitCountValue);
// When an integer and a float multiplied, the accuracy of result may be wrong
const stepRatioScale = digitCount !== 1 ? 0.05 : 0.1;
const amendStepRatio = new Decimal(Math.ceil(stepRatio.div(stepRatioScale).toNumber()))
  .add(correctionFactor)
  .mul(stepRatioScale);

const formatStep = amendStepRatio.mul(digitCountValue);

return allowDecimals ? new Decimal(formatStep.toNumber()) : new Decimal(Math.ceil(formatStep.toNumber()));
```

**Flow:** bail to 0 if rough ≤ 0 → normalize rough step into `[1,10)` by dividing by `10^digitCount` → quantize ratio upward onto a 0.05 grid (0.1 grid when digit count is exactly 1) adding correctionFactor → multiply back by magnitude → ceil to integer when `allowDecimals=false`.
**Invariant:** The output step is always ≥ the input rough step (rounding only goes up), and all arithmetic runs on decimal.js-light Decimals — porting with JS floats reproduces the historical precision bugs this module exists to fix.
**Probe:** `test/util/scale/getNiceTickValues.spec.ts` ("should return bigger step for bigger numbers": `getAdaptiveStep(new Decimal(3.45687e9), true, 0).toNumber()` must be exactly `3.5e9`; "should return smaller step for small numbers" pins `9.6341e-9 → 1e-8`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "getAdaptiveStep", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the whole function including the digit-count-conditional grid (the 0.05-vs-0.1 asymmetry is intentional density tuning) and the up-only rounding direction; adapt `correctionFactor` semantics if your caller has no recursion ladder (pass 0); omit nothing — every branch is reachable. Direct tests exist upstream and are byte-pinned above; index coverage for the file was clean at capture time.
