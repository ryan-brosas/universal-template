<!-- capsule-v2 -->
# Drag state hook — how do dx/dy, controlled dragging, snap-to-pointer, and path restriction compose?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** What is the state shape and update order of a reusable drag primitive that supports BOTH uncontrolled use and a parent-driven `isDragging`?

## useStateWithCallback + dragStartPointerOffset
**Path/Symbol:** `packages/visx-drag/src/useDrag.ts:useDrag` (:71–227); restrict ladder `util/restrictPoint.ts` (:6–18) + `util/useSamplesAlongPath.ts` (:3–20).
**Signature:** `useDrag(options) => {x?,y?,dx,dy,isDragging, dragStart, dragMove, dragEnd}`; handlers take any Mouse/Touch/Pointer event.
**Data Shape:** `DragState = {x?: y? (start pos), dx/dy (delta since start), isDragging}`; callbacks fire AFTER state commits via `useStateWithCallback(state, cb)` — the callback receives the NEW state plus the raw `event`.

### Decisive source
```ts
// start: remember where the element was relative to the pointer
const currentPoint = new Point({ x: (x||0)+dx, y: (y||0)+dy });
const eventPoint = localPoint(event) || new Point({ x: 0, y: 0 });
setDragStartPointerOffset(subtractPoints(currentPoint, eventPoint));
return {
  isDragging: true,
  dx: resetOnStart ? 0 : currState.dx,
  dy: resetOnStart ? 0 : currState.dy,
  x: resetOnStart ? dragPoint.x : dragPoint.x - currState.dx,
  y: resetOnStart ? dragPoint.y : dragPoint.y - currState.dy,
};

// move: element follows pointer + preserved grab offset
const point = snapToPointer ? pointerPoint : sumPoints(pointerPoint, dragStartPointerOffset);

// restriction: path samples WIN over box clamps entirely
if (samples.length > 0) return getClosestPoint(point, samples);
return { x: clampNumber(point.x, restrict.xMin ?? -Infinity, ...), ... };
```

**Flow:** `dragStart` persists the event (React pooling-era guard), computes grab offset, applies `restrictPoint`, resets or keeps dx/dy per `resetOnStart`; `dragMove` no-ops unless `isDragging`; `isDragging` PROP (when defined) syncs via effect for controlled mode (BaseBrush uses this to force-start selects). Path restriction pre-samples `getPointAtLength` every 1px through the path's CTM and snaps to nearest sample.
**Invariant:** dx/dy are always RELATIVE to drag start, and x/y stay the anchor — consumers position with `x+dx`. Restriction precedence is exclusive (path beats box), not additive. `event.persist()` calls must survive porting to legacy React hosts.
**Probe:** `packages/visx-drag/test/useDrag.test.tsx` (state transitions); `test/useStateWithCallback.test.ts` (post-commit callback order).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "useDrag restrictPoint snapToPointer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt state shape + offset math + restriction precedence; adapt to your gesture lib if porting to pointer-capture; omit the `<Drag>` render-prop wrapper.
