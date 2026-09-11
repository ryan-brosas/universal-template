<!-- capsule-v2 -->
# getTicks — which ticks get DISPLAYED when labels collide, per `interval` mode?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** How do preserveStart/preserveEnd/preserveStartEnd and measured label sizes decide the visible subset, and why is getSize lazy?

## Collision-aware display filter
**Path/Symbol:** `src/cartesian/getTicks.ts:getTicks` (:149-197) with `getTicksEnd` (:11-60) / `getTicksStart` (:62-135).
**Signature:** `getTicks(props: GetTicksInput, fontSize?: string, letterSpacing?: string) => ReadonlyArray<CartesianTickItem>`.
**Data Shape:** Input carries candidate ticks `{value, coordinate}`; output adds `tickCoord` + `isShow` and drops hidden entries. Numeric `interval` short-circuits to every-(N+1)-th via `getNumberIntervalTicks`.

### Decisive source
```ts
if (isNumber(interval) || Global.isSsr) {
  return getNumberIntervalTicks(ticks, isNumber(interval) ? interval : 0) ?? [];
}
const sizeKey = orientation === 'top' || orientation === 'bottom' ? 'width' : 'height';
const unitSize = unit && sizeKey === 'width' ? getStringSize(unit, { fontSize, letterSpacing }) : { width: 0, height: 0 };
const getTickSize = (content, index) => {
  const value = typeof tickFormatter === 'function' ? tickFormatter(content.value, index) : content.value;
  return sizeKey === 'width'
    ? getAngledTickWidth(getStringSize(value, { fontSize, letterSpacing }), unitSize, angle)
    : getStringSize(value, { fontSize, letterSpacing })[sizeKey];
};
const sign = ticks.length >= 2 && tick0 != null && tick1 != null ? mathSign(tick1.coordinate - tick0.coordinate) : 1;
const boundaries = getTickBoundaries(viewBox, sign, sizeKey);
if (interval === 'equidistantPreserveStart') return getEquidistantTicks(...);
if (interval === 'equidistantPreserveEnd') return getEquidistantPreserveEndTicks(...);
if (interval === 'preserveStart' || interval === 'preserveStartEnd') {
  candidates = getTicksStart(sign, boundaries, getTickSize, ticks, minTickGap, interval === 'preserveStartEnd');
} else {
  candidates = getTicksEnd(sign, boundaries, getTickSize, ticks, minTickGap);
}
return candidates.filter(entry => entry.isShow);
```
```ts
const getSize = () => {
  if (size === undefined) {
    size = getTickSize(initialEntry, i); // DOM read: expensive
  }
  return size;
};
```

**Flow:** numeric-interval/SSR bypass → derive sweep direction `sign` from first two coordinates (reversed axes flip everything) → viewBox edges become signed [start,end] → END modes walk right-to-left shrinking `end` by `size/2+minTickGap` after each shown tick; START modes walk left-to-right growing `start` the same way, with `preserveStartEnd` first guaranteeing the tail then filling from the head; edge ticks get their `tickCoord` pulled inward when they'd overflow the boundary.
**Invariant:** `getSize()` is memoized-per-tick BECAUSE it measures the DOM (`getStringSize`) — calling it unconditionally multiplies layout reads and was the original perf bug; visibility check order (`isVisible` tests bounds BEFORE invoking getSize) preserves that guarantee.
**Probe:** `test/cartesian/getTicks.spec.ts` mocks `getStringSize` to `({width: text.length, height: 12})` and pins whole arrays per mode ("ticks are always shown if there is space" — `preserveEnd`/`preserveStart` expectations list all six ticks with `isShow: true`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "getTicks", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the direction-sign + lazy-size + gap-shrink machinery wholesale; adapt measurement (`getStringSize`) to your DOM layer but keep its laziness; omit SSR branch only if you never server-render.
