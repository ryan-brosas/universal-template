<!-- capsule-v2 -->
# getTickValuesFixedDomain — how do you get nice steps WITHOUT extending the domain?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** How does the fixed-domain variant differ from `getNiceTickValues` in boundary handling, count guarantees, and integer cleanup?

## Domain-clamped tick generator
**Path/Symbol:** `src/util/scale/getNiceTickValues.ts:getTickValuesFixedDomain` (:275-315).
**Signature:** `getTickValuesFixedDomain([min, max]: NumberDomain, tickCount: number, allowDecimals = true, niceTicksMode: NiceTicksAlgorithm = 'auto') => number[]`.
**Data Shape:** Same inputs as `getNiceTickValues`; output always starts at cormin and ends at exactly cormax; may return FEWER ticks than requested when the range is too small.

### Decisive source
```ts
const [cormin, cormax] = getValidInterval([min, max]);
if (cormin === -Infinity || cormax === Infinity) {
  return [min, max]; // passthrough — no sentinel fill here
}
if (cormin === cormax) {
  return [cormin];  // single element, NOT the centered fan
}
const stepFn = niceTicksMode === 'snap125' ? getSnap125Step : getAdaptiveStep;
const count = Math.max(tickCount, 2);
const step = stepFn(new Decimal(cormax).sub(cormin).div(count - 1), allowDecimals, 0);
let values = [...rangeStep(new Decimal(cormin), new Decimal(cormax), step), cormax];
if (allowDecimals === false) {
  values = values.map(value => Math.round(value));
  const last = values.length - 1;
  if (last > 0 && values[last] === values[last - 1]) {
    values = values.slice(0, last); // dedupe trailing tick after rounding
  }
}
return min > max ? values.reverse() : values;
```

**Flow:** infinite/equal guards SHORT-CIRCUIT differently from the extension variant (raw `[min,max]` / `[value]`) → one-shot step (correctionFactor pinned to 0, NO recursion ladder) → walk from min and force-append cormax so the boundary is always a tick → in integer mode round everything AFTER stepping (the first tick may be decimal even with an integer step) then drop the duplicate created when cormax rounds onto the last stepped value.
**Invariant:** The appended-boundary + post-round dedupe pair is atomic — removing either half ships either duplicated trailing ticks or a missing domain edge. Count is best-effort ("may return less than tickCount if the interval is too small" per doc).
**Probe:** `test/util/scale/getTickValuesFixedDomain.spec.ts` ("returns fewer ticks than requested for close values": `getTickValuesFixedDomain([1, 7], 5)` equals `[1,3,5,7]` with length < count; "of unequal values of positive integer" pins `[1,70],5 → [1,21,41,61,70]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "getTickValuesFixedDomain", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt both generators as a matched pair selected by whether the axis domain may grow ('auto' keyword present → extension variant; fixed numeric domain → this one — that routing lives in `combineNiceTicks`); adapt the integer-cleanup if your labels tolerate decimals; omit nothing.
