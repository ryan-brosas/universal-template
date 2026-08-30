<!-- capsule-v2 -->
# Geometry primitives — Shape contract, Rectangle algebra, exceedsDistance dialects

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** Which geometry operations must a porter reimplement exactly, and where do the two distance-comparison dialects differ?

## @dnd-kit/geometry core
**Path/Symbol:** `packages/geometry/src/shapes/Shape.ts:10-68` (abstract contract), `shapes/Rectangle.ts`, `point/Point.ts` (delta/distance/equals statics), `distance/distance.ts:7-34` (`exceedsDistance`).
**Signature:** `Shape` requires `boundingRectangle, center, area, scale, inverseScale, aspectRatio, equals, intersectionArea, containsPoint`; `Point.distance(a,b) = Math.hypot(dx, dy)`; `exceedsDistance(coords, distance)` over `Distance = number | {x?, y?}`.
**Data Shape:** DOMRectangle implements Shape from live elements (with frame-transform normalization); Rectangle is the plain-rect workhorse with translate/intersection utilities.

### Decisive source
```ts
export function exceedsDistance({x, y}: Coordinates, distance: Distance): boolean {
  const dx = Math.abs(x);
  const dy = Math.abs(y);

  if (typeof distance === 'number') {
    return Math.sqrt(dx ** 2 + dy ** 2) > distance;      // Euclidean magnitude
  }
  if ('x' in distance && 'y' in distance) {
    return dx > distance.x && dy > distance.y;           // AND over BOTH axes
  }
  if ('x' in distance) return dx > distance.x;
  if ('y' in distance) return dy > distance.y;
  return false;
}
```

**Flow:** sensors use the NUMBER form for activation tolerances ("moved more than N px overall"); DelayConstraint tolerance accepts either form — the object form means "cancel only when movement exceeds on both axes" which is what makes long-press tolerant of small diagonal drift. Collision math leans on Point.distance and Rectangle.intersectionArea; drop animations need `Rectangle.delta(current, final, alignment)`.
**Invariant:** number = Euclidean OR-threshold; `{x,y}` object = AND per-axis — conflating them silently changes activation feel (verified by live probe: `{x:3,y:4}` vs 5 → false, vs 4.9 → true; `{x:10,y:1}` vs {5,5} → false because AND); Shape.equals drives shape-cache dedupe so it must compare ALL geometry-bearing fields.
**Probe:** `exceedsDistance` live-executed matrix (both dialects + single-axis forms); `deepEqual` comparators suite GREEN upstream; no dedicated geometry unit file ships (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "Rectangle Shape", name_pattern: "^Shape$", limit: 10 });
```

## Verdict
Adopt the Shape interface and both distance dialects verbatim; adapt Rectangle/DOMRectangle internals to your transform model but preserve equals/intersectionArea semantics consumers rely on; omit inverseScale plumbing only for untransformed layouts.
