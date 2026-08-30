<!-- capsule-v2 -->
# isVisible + getTickBoundaries + getEveryNth — the signed-axis visibility algebra every tick filter shares

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** How do three tiny helpers let ONE collision algorithm serve left-to-right, right-to-left, horizontal, vertical, AND angle axes?

## Signed-space visibility primitives
**Path/Symbol:** `src/util/TickUtils.ts:isVisible` (:26-42), `src/util/TickUtils.ts:getTickBoundaries` (:11-24), `src/util/getEveryNth.ts:getEveryNth` (:12-27).
**Signature:** `isVisible(sign, tickPosition, getSize: () => number, start, end) => boolean`; `getTickBoundaries(viewBox, sign, sizeKey) => {start, end}`; `getEveryNth<T>(array, n) => ReadonlyArray<T>`.
**Data Shape:** All coordinates live in "signed space": multiplying by `sign` (±1) makes descending axes look ascending to the algorithm; `sizeKey` picks width (horizontal orientations) or height.

### Decisive source
```ts
export function isVisible(sign, tickPosition, getSize, start, end) {
  /* Since getSize() is expensive (it reads the ticks' size from the DOM), we do this check first
   * to avoid calculating the tick's size. */
  if (sign * tickPosition < sign * start || sign * tickPosition > sign * end) {
    return false;
  }
  const size = getSize();
  return sign * (tickPosition - (sign * size) / 2 - start) >= 0 && sign * (tickPosition + (sign * size) / 2 - end) <= 0;
}
```
```ts
if (sign === 1) {
  return { start: isWidth ? x : y, end: isWidth ? x + width : y + height };
}
return { start: isWidth ? x + width : y + height, end: isWidth ? x : y }; // swapped for reversed axis
```
```ts
if (n < 1) return [];
if (n === 1) return array; // identity, not a copy — callers must not mutate
```

**Flow:** boundaries swap start/end under negative sign so every consumer walks "increasing" coordinates regardless of direction → visibility first tests the cheap center-in-range predicate, and only then pays the DOM read to check `[pos−size/2, pos+size/2] ⊆ [start,end]` → numeric-interval filtering delegates to getEveryNth(ticks, interval+1) with n<1 → [] and n=1 identity semantics.
**Invariant:** The bounds-before-size ordering inside isVisible is a documented performance invariant (comment in source); the ±1 in `getNumberIntervalTicks` (interval N means skip N−1 between) lives in the CALLER. `getEveryNth`'s identity return at n===1 leaks the input array — filters downstream treat it read-only.
**Probe:** `test/cartesian/getTicks.spec.ts` pins interval behavior end-to-end ("ticks are always shown if there is space" matrix); `grep -n "getSize() is expensive" src/util/TickUtils.ts` → exactly 1 hit at :33.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "isVisible", limit: 5, fields: ["signature", "name", "file"] });
```
Live-verified line-exact TickUtils :26-42.

## Verdict
Adopt all three as the shared substrate of any tick-display port; adapt `getSize` backing (DOM measure vs canvas estimate) but never reorder its call after the range test; omit nothing.
