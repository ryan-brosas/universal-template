<!-- capsule-v2 -->
# getEquidistantTicks / getEquidistantPreserveEndTicks — how does step-size search pick evenly spaced visible ticks?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** Why does the start-anchored variant restart the whole sweep when one tick collides, and how does the end-anchored variant guarantee the last tick instead?

## Step-doubling search pair
**Path/Symbol:** `src/cartesian/getEquidistantTicks.ts:getEquidistantTicks` (:6-64), `src/cartesian/getEquidistantTicks.ts:getEquidistantPreserveEndTicks` (:66-143).
**Signature:** Both: `(sign: Sign, boundaries {start,end}, getTickSize, ticks, minTickGap) => ReadonlyArray<CartesianTickItem>`.
**Data Shape:** Output is a strict arithmetic subsequence of input indices (start-anchored: offset 0; end-anchored: offset `(len-1)%stepsize`).

### Decisive source (start-anchored core loop)
```ts
while (stepsize <= result.length) {
  const entry = ticks?.[index];
  if (entry === undefined) {
    return getEveryNth(ticks, stepsize); // evaluated all: done
  }
  const isShow = index === 0 || isVisible(sign, tickCoord, getSize, start, end);
  if (!isShow) {
    // Start all over with a larger stepsize
    index = 0;
    start = initialStart;
    stepsize += 1;
  }
  if (isShow) {
    start = tickCoord + sign * (getSize() / 2 + minTickGap);
    index += stepsize;
  }
}
return [];
```
```ts
// preserve-end variant: iterate the END-ANCHORED sequence for this stepsize
const offset = (len - 1) % stepsize;
for (let index = offset; index < len; index += stepsize) {
  const isShow = index === offset || isVisible(sign, tickCoord, getSize, start, end);
  if (!isShow) { ok = false; break; }   // reject this stepsize, try next
  if (isShow) { start = tickCoord + sign * (getSize() / 2 + minTickGap); }
}
if (ok) { /* rebuild finalTicks from offset stepping by stepsize */ return finalTicks; }
```

**Flow (both):** try stepsize = 1, 2, 3… — for each, walk the anchored arithmetic sequence checking collision-free visibility with per-tick gap accounting; first FULLY passing stepsize wins. Start variant resets `index` AND `start` on any failure (restart semantics); end variant computes its offset so index `len-1` is always IN the sequence and validates forward from there.
**Invariant:** "Always show the first" (or last) is enforced by the `index === 0` (resp. `index === offset`) bypass — not by skipping checks for it later; both return `[]` only when even the largest stepsize cannot fit (huge minTickGap). The upstream matrix test documents that results are NOT monotone-friendly (e.g. 10 ticks fitting 5 → `[0,5]`, not every-other).
**Probe:** `test/cartesian/getEquidistantTicks.spec.ts` test.each matrix ("should skip ticks to satisfy minTickGap while preserving the end tick": five ticks at spacing 10 with size 10 + minTickGap 8 → indices `[0,2,4]` returned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "getEquidistantPreserveEndTicks", limit: 5, fields: ["signature", "name", "file"] });
```
Live-verified line-exact :66-143.

## Verdict
Adopt the restart-vs-offset asymmetry exactly — it is what makes 'equidistantPreserveStart' and 'equidistantPreserveEnd' visibly different; adapt `isVisible` only via the shared TickUtils capsule; omit nothing.
