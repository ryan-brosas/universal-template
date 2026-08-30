<!-- capsule-v2 -->
# Pixel-to-domain brush conversion — how do you turn a dragged rectangle into data values for BOTH continuous and ordinal scales?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** Ordinal scales have no `.invert()` — how does the Brush report which categories fall inside a selection, and why nudge pixels by ±2?

## scaleInvert fallback + SAFE_PIXEL tolerance
**Path/Symbol:** `packages/visx-brush/src/utils.ts:scaleInvert` (:5–27) + `getDomainFromExtent` (:29–57); consumer `Brush.tsx:convertRangeToDomain` (:123–140), `handleBrushStart` (:142–159).
**Signature:** `scaleInvert(scale: Scale, value: number): number|Date|any` ; `getDomainFromExtent(scale, start, end, tolerentDelta): {start?, end?, values?}`.
**Data Shape:** continuous result `{start,end}`; ordinal result `{values: domain[i0..i1]}` — the two shapes are MUTUALLY EXCLUSIVE and consumers must check which came back (`Bounds` carries optional `xValues`/`yValues`).

### Decisive source
```ts
// ordinal fallback: index = how many steps from range start
const step = 'step' in scale && typeof scale.step !== 'undefined' ? scale.step() : 1;
const width = (step * (end - start)) / Math.abs(end - start);  // ±1 direction
if (width > 0) { while (value > start + width * (i + 1)) i += 1; }
else           { while (value < start + width * (i + 1)) i += 1; }
```
```ts
// nudge outward by SAFE_PIXEL=2 so a zero-width edge still catches its band
const invertedStart = scaleInvert(scale, start + (start < end ? -tolerentDelta : tolerentDelta));
const invertedEnd   = scaleInvert(scale, end   + (end < start ? -tolerentDelta : tolerentDelta));
```

**Flow:** Brush.handleChange/handleBrushEnd gate on `extent.x0 >= 0` else emit `null` → convertRangeToDomain inverts both axes with the ±SAFE_PIXEL nudge → min/max normalize → continuous: numeric/date span; ordinal: slice of `scale.domain()`. `handleBrushStart` mirrors the same invert-vs-`domain()[index]` branch.
**Invariant:** the ±delta is applied OUTWARD on each edge (start gets `-` when start<end) so single-pixel selections still include their nearest category; dropping it makes click-selects return empty ranges. The direction-aware `width` sign handles reversed ranges — using plain `(end-start)` breaks mirrored scales.
**Probe:** `packages/visx-brush/test/utils.test.ts` (invert + domain-from-extent cases incl. band scales).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "scaleInvert ordinal step", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "Brush convertRangeToDomain getDomainFromExtent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt both functions verbatim (pure scale math); adapt `Scale` type union to your scale set; omit margin/region layout logic if you don't support axis-region brushing.
