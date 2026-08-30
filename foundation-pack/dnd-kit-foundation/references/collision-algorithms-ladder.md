<!-- capsule-v2 -->
# Collision algorithms — value semantics, priority vocabulary, and the fallback ladders

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** What do the shipped detectors return exactly (value units, types, priorities), and how do they compose?

## Algorithm family
**Path/Symbol:** `packages/collision/src/algorithms/{default,pointerIntersection,shapeIntersection,closestCenter,closestCorners,pointerDistance,directionBiased}.ts` + abstract enums `CollisionType/CollisionPriority` (`packages/abstract/src/core/collision/types.ts`) + sort in `utilities.ts:7-17`.
**Signature:** every detector is `(input: {dragOperation, droppable}) => Collision | null`; `Collision = {id, value: number (higher = better), type, priority}`.
**Data Shape:** pointerIntersection → `type: PointerIntersection`, `priority: High`, `value = 1 / distance(pointer→center)`; shapeIntersection → area-based; closestCenter/pointerDistance fall back through `defaultCollisionDetection` first and otherwise emit `1/distance` with `CollisionType.Collision`, `priority: Normal`.

### Decisive source
```ts
// default.ts — the whole ladder
export const defaultCollisionDetection: CollisionDetector = (args) => {
  return pointerIntersection(args) ?? shapeIntersection(args);
};

// pointerIntersection.ts — why 1/distance
if (droppable.shape.containsPoint(pointerCoordinates)) {
  /* There may be more than a single rectangle intersecting
   * with the pointer coordinates. In order to sort the
   * colliding rectangles, we measure the distance between
   * the pointer and the center of the intersecting rectangle */
  const distance = Point.distance(droppable.shape.center, pointerCoordinates);
  return { id, value: 1 / distance,
           type: CollisionType.PointerIntersection,
           priority: CollisionPriority.High };
}

// closestCenter.ts — overlap wins, then proximity
const collision = defaultCollisionDetection(input);
if (collision) return collision;
const distance = Point.distance(droppable.shape.center,
                                shape?.current.center ?? position.current);
return { id: droppable.id, value: 1 / distance,
         type: CollisionType.Collision, priority: CollisionPriority.Normal };
```

**Flow:** observer invokes each eligible droppable's detector (per-droppable override possible) → null means "no collision" and contributes nothing → results sorted priority desc → type desc → value desc. Value is deliberately an inverse-distance so SMALLER raw distances produce LARGER scores under one uniform "higher wins" sort; type ranks pointer-intersections above shape intersections at equal priority so the pointer's exact hover beats a big-area overlap.
**Invariant:** detectors must be pure w.r.t. their inputs (they run untracked inside the observer); returning a shape-based result when the pointer intersects would break nested-container disambiguation — always prefer the pointer plane first; `droppable.collisionPriority` overrides the algorithm default AFTER detection (observer :141-143).
**Probe:** algorithm contracts exercised via kernel suites (custom detector in drag-event-order.test.ts returns the documented shape); geometry helpers pinned by live probes of `Point.distance`/`exceedsDistance` semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "closestCenter pointerIntersection", name_pattern: "^closestCenter$", limit: 10 });
```

## Verdict
Adopt the `{id,value,type,priority}` contract and the pointer-first composition ladder; adapt the numeric vocabularies to your ranking needs but keep "higher wins" + inverse-distance convention or re-tune every consumer; omit directionBiased unless building axis-locked sortables.
