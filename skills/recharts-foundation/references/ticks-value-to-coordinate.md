<!-- capsule-v2 -->
# combineAxisTicks — how do raw tick VALUES become pixel coordinates, and which source wins?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** What is the precedence order (user ticks → niceTicks → categorical domain → scale.ticks → domain walk) and how are band offsets computed per axis type?

## Tick value → TickItem funnel
**Path/Symbol:** `src/state/selectors/axisSelectors.ts:combineAxisTicks` (:1992-2093).
**Signature:** `combineAxisTicks(layout, axis: RenderableAxisSettings, realScaleType?, scale?: RechartsScale, niceTicks?, axisRange?, duplicateDomain?, categoricalDomain?, axisType) => ReadonlyArray<TickItem> | undefined`.
**Data Shape:** Output `{ value, coordinate, index, offset }[]` — coordinate is scaled+offset pixels; null entries (non-finite scaled values via `isWellBehavedNumber`) are filtered.

### Decisive source
```ts
const offsetForBand =
  realScaleType === 'scaleBand' && typeof scale.bandwidth === 'function' ? scale.bandwidth() / 2 : 2;
let offset = type === 'category' && scale.bandwidth ? scale.bandwidth() / offsetForBand : 0;
offset =
  axisType === 'angleAxis' && axisRange != null && axisRange.length >= 2
    ? mathSign(axisRange[0] - axisRange[1]) * 2 * offset
    : offset;
// The ticks set by user should only affect the ticks adjacent to axis line
const ticksOrNiceTicks = ticks || niceTicks;
if (ticksOrNiceTicks) {
  return ticksOrNiceTicks.map((entry, index) => {
    const scaleContent = duplicateDomain ? duplicateDomain.indexOf(entry) : entry;
    const scaled = scale.map(scaleContent);
    if (!isWellBehavedNumber(scaled)) {
      return null;
    }
    return { index, coordinate: scaled + offset, value: entry, offset };
  }).filter(isNotNil);
}
if (isCategorical && categoricalDomain) { /* map each category */ }
if (scale.ticks) {
  return scale.ticks(tickCount).map(/* same shape, d3-chosen values */);
}
return scale.domain().map(/* serial-number fallback for duplicated text */);
```

**Flow:** compute band half-width offset only for category axes (divisor 2 normally, bandwidth/2 when the real type is scaleBand — the @ts-expect-error documents this dead-looking branch); angle axes SIGN-DOUBLE the offset by range direction; then five-level precedence: user ticks/niceTicks first (mapped through `duplicateDomain.indexOf` so repeated labels still position), categorical domain second, d3 `scale.ticks(tickCount)` third, raw domain walk last.
**Invariant:** The `#4271` comment is load-bearing: for `type='number'` + linear + available niceTicks the categorical branch must be SKIPPED or ticks land at data positions instead of evenly spaced. Every mapped entry filters non-finite coordinates (`isWellBehavedNumber` = Number.isFinite).
**Probe:** `grep -n "ticksOrNiceTicks = ticks || niceTicks" src/state/selectors/axisSelectors.ts` → exactly 1 hit at :2023; issue-comment pin `grep -n "GitHub issue #4271" src/state/selectors/axisSelectors.ts` → exactly 1 hit at :2045.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "combineAxisTicks", limit: 5, fields: ["signature", "name", "file"] });
```
Live-verified line-exact :1992-2093; sibling implementations noted in-source as "the four horsemen of tick generation" (tooltip/graphical-item variants share the shape).

## Verdict
Adopt the precedence ladder and both band-offset quirks (scaleBand divisor + angle sign-doubling); adapt the duplicateDomain handling if your data forbids repeated categories; omit the three sibling tick generators unless you port tooltips too.
