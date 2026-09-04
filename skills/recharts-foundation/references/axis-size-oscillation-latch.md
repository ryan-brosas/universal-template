<!-- capsule-v2 -->
# cartesianAxisSlice width/height oscillation latch — why do axis size updates stop by themselves?

**Source:** recharts MIT `main@d56d6660f7db52d37cb2113b39a2be010d32fe37`; Codebase Memory `ext-ui-recharts`. **Question:** How does the A→B→A detector distinguish a layout feedback loop from a legitimate size change, and what breaks without it?

## Oscillation-detecting reducers
**Path/Symbol:** `src/state/cartesianAxisSlice.ts:updateYAxisWidth` (:249-272), `updateXAxisHeight` (:273-296).
**Signature:** `updateYAxisWidth(state, action: PayloadAction<{ id: AxisId; width: number }>)` (same shape for X heights).
**Data Shape:** Each axis settings object carries `widthHistory`/`heightHistory?: number[]` capped to last 3 entries; `'auto'` is a legal current value.

### Decisive source
```ts
const history = axis.widthHistory || [];
// An oscillation is detected when the new width is the same as the width before the last one.
// This is a simple A -> B -> A pattern. If the next width is B, and the difference is less
// than 1 pixel, we ignore it.
if (
  history.length === 3 &&
  history[0] === history[2] &&
  width === history[1] &&
  width !== axis.width &&
  Math.abs(width - (history[0] ?? 0)) <= 1
) {
  return; // swallow the update: state stays at B forever, loop broken
}
const newHistory = [...history, width].slice(-3);
state.yAxis[id] = {
  ...axis,
  width,
  widthHistory: newHistory,
};
```

**Flow:** axis measures itself → dispatches its pixel width → reducer appends to a 3-slot ring. When the ring shows A,B,A AND the incoming width is B again AND |B−A| ≤ 1px, the update is DROPPED — freezing the axis at B so React stops re-rendering. Differences >1px bypass the latch (#6424: large swings are intentional user resizes, not jitter).
**Invariant:** All five conditions are required together — dropping `width !== axis.width` would freeze legitimate monotonic growth; dropping the 1px guard would freeze real resizes. History is appended BEFORE the cap (`slice(-3)`) and only in the accept path.
**Probe:** `test/state/selectors/cartesianAxisSlice.spec.ts` ("should stop updating width after oscillation is detected": dispatches 50→51→50 then 51 is IGNORED — state stays 50; "should keep updating if the oscillation is larger than 1 pixel" pins 50→52→50 then 52 IS accepted per issue #6424).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-recharts", query: "cartesianAxisSlice", limit: 5, fields: ["signature", "name", "file"] });
```
Live-verified: `search_graph "updateYAxisWidth"` = total:0 (action creators are exported consts, not graph Function nodes) — Retrieve targets the slice file node instead.

## Verdict
Adopt the five-condition latch verbatim for ANY measured-axis port; adapt slot count only with evidence (3 is what makes ABA detectable); omit redux specifics but keep the ring-history state on your settings object.
