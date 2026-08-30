<!-- capsule-v2 -->
# createCategoricalInverse + bisect — how do you map a pixel BACK to a category?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** How is nearest-category inversion implemented for scales lacking `invert`, and why does it accept an explicit data-point list?

## Pixel→domain nearest-neighbor search
**Path/Symbol:** `src/util/scale/createCategoricalInverse.ts:bisect` (:14-28), `createCategoricalInverse` (:34-71).
**Signature:** `bisect(haystack: ReadonlyArray<number>, needle: number) => number`; `createCategoricalInverse(scale?: CustomScaleDefinition, allDataPointsOnAxis?: ReadonlyArray<unknown>) => InverseScaleFunction | undefined`.
**Data Shape:** Precomputes one pixel position per domain entry; returned closure maps pixel → domain value (never undefined except empty-domain/range construction failure).

### Decisive source
```ts
export function bisect(haystack: ReadonlyArray<number>, needle: number): number {
  let lo = 0;
  let hi = haystack.length;
  const ascending = haystack[0]! < haystack[haystack.length - 1]!;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (ascending ? haystack[mid]! < needle : haystack[mid]! > needle) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  return lo;
}
```
```ts
const domain = allDataPointsOnAxis ?? scale.domain();
const pixelPositions: number[] = domain.map(d => scale(d) ?? 0);
if (domain.length === 0 || range.length < 2) {
  return undefined;
}
return (pixelValue: number): unknown => {
  const index = bisect(pixelPositions, pixelValue);
  if (index <= 0) return domain[0];
  if (index >= domain.length) return domain[domain.length - 1];
  const leftPixel = pixelPositions[index - 1] ?? 0;
  const rightPixel = pixelPositions[index] ?? 0;
  if (Math.abs(pixelValue - leftPixel) <= Math.abs(pixelValue - rightPixel)) {
    return domain[index - 1];
  }
  return domain[index];
};
```

**Flow:** build pixel positions ONCE per scale (closure cache) → bisect handles ASCENDING and DESCENDING arrays via the two-sided comparison (d3.bisect only ascends) → clamp out-of-range pixels to end domains → tie-break to the LEFT neighbor on exact equidistance (`<=`). The optional `allDataPointsOnAxis` overrides the scale's own domain so tooltips can snap against DATA points that differ from the axis domain.
**Invariant:** Positions array and domain share index order — any sort applied to one must apply to both; the descending-array support in `bisect` is the delta vs d3.bisect and is directly unit-tested. Empty domains and sub-2-length ranges refuse to build an inverse rather than returning a degenerate closure.
**Probe:** `test/util/scale/createCategoricalInverse.spec.ts` ("should return the correct insertion index in a descending array": `bisect([9,7,5,3,1], 6)` = `2`; nearest-pick cases pin left-tie-breaking).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "createCategoricalInverse", limit: 5, fields: ["signature", "name", "file"] });
```
Live-verified line-exact :34-71; wired as `selectAxisInverseDataSnapScale = createSelector([selectConfiguredScale, selectSortedDataPoints], createCategoricalInverse)` (:1657+).

## Verdict
Adopt both functions including direction detection and left tie-break; adapt the data-points override to your tooltip snapping model; omit nothing — every branch has an upstream test.
