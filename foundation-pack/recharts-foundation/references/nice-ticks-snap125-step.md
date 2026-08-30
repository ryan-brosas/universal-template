<!-- capsule-v2 -->
# getSnap125Step — how does the opt-in "pretty numbers" algorithm snap steps to {1,2,2.5,5}×10ⁿ?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** How does the snap125 ladder map an arbitrary rough step onto the nice-step set, and how does correctionFactor walk that set instead of adding to it?

## Nice-number snapping ladder
**Path/Symbol:** `src/util/scale/getNiceTickValues.ts:getSnap125Step` (:72-106).
**Signature:** `getSnap125Step: StepFunction = (roughStep: Decimal, allowDecimals: boolean, correctionFactor: number) => Decimal`.
**Data Shape:** Same contract as `getAdaptiveStep` (both satisfy `StepFunction`). Output step ∈ {1, 2, 2.5, 5} × 10ⁿ (or its integer ceil).

### Decisive source
```ts
const NICE_STEPS = [1, 2, 2.5, 5];
const roughNum = roughStep.toNumber();
const exponent = Math.floor(new Decimal(roughNum).abs().log(10).toNumber());
let magnitude = new Decimal(10).pow(exponent);
// normalized is in the range [1, 10)
const normalized = roughStep.div(magnitude).toNumber();
// Find the smallest nice step >= normalized (ceiling)
let niceIdx = NICE_STEPS.findIndex(s => s >= normalized - 1e-10);
if (niceIdx === -1) {
  // normalized > 5 (e.g. 7.3), move to next order of magnitude
  magnitude = magnitude.mul(10);
  niceIdx = 0;
}
// Apply correction factor by stepping through the nice number sequence
niceIdx += correctionFactor;
if (niceIdx >= NICE_STEPS.length) {
  const extraMag = Math.floor(niceIdx / NICE_STEPS.length);
  niceIdx %= NICE_STEPS.length;
  magnitude = magnitude.mul(new Decimal(10).pow(extraMag));
}
const niceStep = NICE_STEPS[niceIdx] ?? 1;
const formatStep = new Decimal(niceStep).mul(magnitude);
return allowDecimals ? formatStep : new Decimal(Math.ceil(formatStep.toNumber()));
```

**Flow:** bail to 0 → decompose rough step into magnitude × normalized ∈ [1,10) → ceiling-search the ladder with a `1e-10` epsilon so exact members (2.5) stay put — a plain float compare would skip them → overflow past 5 bumps one full magnitude → **correctionFactor ADVANCES THE INDEX through the cyclic ladder** (wrapping carries into extra magnitudes), unlike adaptive's additive grid nudge.
**Invariant:** The result is always ≥ rough step and always exactly representable in binary-friendly decimal form; the epsilon guard on exact members is load-bearing (`getSnap125Step(Decimal(2.5), true, 0)` must be `2.5`, not `5`).
**Probe:** `test/util/scale/getNiceTickValues.spec.ts` ("should snap up to next order of magnitude when normalized > 5": `getSnap125Step(new Decimal(7.3), true, 0).toNumber() === 10`; "exact member" case pins `new Decimal(2.5)` unchanged).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "getSnap125Step", limit: 5, fields: ["signature", "name", "file"] });
```
Live-verified: resolves line-exact at :72-106.

## Verdict
Adopt both algorithms as interchangeable `StepFunction`s selected by the axis `niceTicks` prop ('auto'/'adaptive' → adaptive, 'snap125' → this); adapt the epsilon if your language compares decimals natively; omit nothing. Upstream direct tests cover every branch including the wrap-around.
