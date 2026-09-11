<!-- capsule-v2 -->
# getTickOfSingleValue — what do ticks look like when min === max?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** When every datum has the same value, how are tickCount ticks centered on it under the decimals/zero sub-cases?

## Degenerate-domain centering
**Path/Symbol:** `src/util/scale/getNiceTickValues.ts:getTickOfSingleValue` (:116-147).
**Signature:** `getTickOfSingleValue(value: number, tickCount: number, allowDecimals: boolean) => Array<number>`.
**Data Shape:** One scalar + count; returns exactly `tickCount` consecutive values with step 1 (except the <1 decimal branch) symmetric around a computed middle.

### Decisive source
```ts
if (!middle.isint() && allowDecimals) {
  const absVal = Math.abs(value);
  if (absVal < 1) {
    // The step should be a float number when the difference is smaller than 1
    step = new Decimal(10).pow(getDigitCount(value) - 1);
    middle = new Decimal(Math.floor(middle.div(step).toNumber())).mul(step);
  } else if (absVal > 1) {
    // Return the maximum integer which is smaller than 'value' when 'value' is greater than 1
    middle = new Decimal(Math.floor(value));
  }
} else if (value === 0) {
  middle = new Decimal(Math.floor((tickCount - 1) / 2));
} else if (!allowDecimals) {
  middle = new Decimal(Math.floor(value));
}
const middleIndex = Math.floor((tickCount - 1) / 2);
const ticks: Array<number> = [];
for (let i = 0; i < tickCount; i++) {
  ticks.push(middle.add(new Decimal(i - middleIndex).mul(step)).toNumber());
}
```

**Flow:** fractional + decimals allowed → |v|<1 floors onto a power-of-ten grid (`step = 10^(digitCount-1)`), |v|>1 floors to integer; value 0 → middle becomes the index midpoint so ticks run 0,1,2,…; integers or no-decimals mode floor to integer; then emit `middle ± k·step` for `k` spanning the count.
**Invariant:** For `[5,5]×3` output is `[4,5,6]`; for `[0.05,0.05]×3` with decimals it is `[0.04,0.05,0.06]` but WITHOUT decimals it degrades to `[-1,0,1]` (the abs<1 grid step still applies then gets ceil-rounded by callers' expectations — pinned upstream). The asymmetry between "isint" and "===0" branches matters: 0 is an int yet takes the midpoint path.
**Probe:** `test/util/scale/getNiceTickValues.spec.ts` ("should generate ticks for single value": `getTickOfSingleValue(5, 5, true)` equals `[3,4,5,6,7]`; "should generate 3 ticks for single value with decimal between 0 and 1" pins `(0.5, 3, false)` → `[-1,+0,1]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "getTickOfSingleValue", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt all four branches and the centered emission loop; adapt only if your axis hides degenerate domains earlier in the pipeline (recharts does not); omit nothing.
