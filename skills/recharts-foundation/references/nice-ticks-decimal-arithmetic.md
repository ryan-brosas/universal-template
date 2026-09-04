<!-- capsule-v2 -->
# rangeStep + getDigitCount — why is tick walking done in Decimal and how do negative digit counts work?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** What precision invariants must the arithmetic helpers keep for tick generation to be stable across 1e-9…1e21 domains?

## Decimal-walk helpers
**Path/Symbol:** `src/util/scale/util/arithmetic.ts:rangeStep` (:38-52), `src/util/scale/util/arithmetic.ts:getDigitCount` (:17-27).
**Signature:** `rangeStep(start: Decimal, end: Decimal, step: Decimal) => number[]`; `getDigitCount(value: number) => Integer`.
**Data Shape:** `rangeStep` accumulates Decimals but pushes plain numbers; `getDigitCount` returns NEGATIVE counts below 1 (0 for [0.1,1), −1 for [0.01,0.1), …).

### Decisive source
```ts
function getDigitCount(value: number) {
  let result;
  if (value === 0) {
    result = 1;
  } else {
    result = Math.floor(new Decimal(value).abs().log(10).toNumber()) + 1;
  }
  return result;
}
```
```ts
// magic number to prevent infinite loop
while (num.lt(end) && i < 100000) {
  result.push(num.toNumber());
  num = num.add(step);
  i++;
}
```

**Flow:** digit count = floor(log10|v|)+1 with the zero→1 special case — this feeds BOTH step algorithms' magnitude normalization; rangeStep walks half-open [start,end) accumulating on Decimals so 0.1-steps produce exactly `[0.1,0.2,…]` without float drift, converting to JS number only at push time.
**Invariant:** The 100000 iteration cap is a deliberate infinite-loop fuse (zero or negative steps upstream); porters who "clean it up" to a while-true re-introduce the hang. Digit-count sign handling is what lets tiny domains (1e-8 ranges) get sensible grids at all.
**Probe:** `test/util/scale/arithmetic.spec.ts` ("should return -2 for value in [0.001, 0.01)": `getDigitCount(0.001)` = `-2`; "should generate correct decimal range steps": `rangeStep(new Decimal(0), new Decimal(1), new Decimal(0.1))` equals `[0,0.1,…,0.9]` exactly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "rangeStep", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt both verbatim including the cap and negative digit counts; adapt only if your host has native decimal arithmetic (keep the cap anyway); omit nothing.
