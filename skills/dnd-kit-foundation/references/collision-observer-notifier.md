<!-- capsule-v2 -->
# Collision observer + notifier — reactive recomputation with an event-loop kill switch

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** When do collisions recompute, how are results ordered, and why does the notifier DISABLE the observer while changing the drop target?

## CollisionObserver / CollisionNotifier pair
**Path/Symbol:** `packages/abstract/src/core/collision/observer.ts:25-167` + `notifier.ts:10-70` + ordering `utilities.ts:7-17`.
**Signature:** `computeCollisions(entries?, detector?): Collision[]`; each collision `{id, value (higher wins), type: CollisionType, priority: CollisionPriority}`; per-droppable detector defaults to `entry.collisionDetector`, falling back through `defaultCollisionDetection = pointerIntersection ?? shapeIntersection`.
**Data Shape:** collisions sorted by `sortCollisions`: priority desc → type desc → value desc; empty-array sentinel `DEFAULT_VALUE` short-circuits no-op publishes.

### Decisive source
```ts
// observer.ts effect body
const collisions = this.computeCollisions();
const coordinates = untracked(() => this.manager.dragOperation.position.current);
if (collisions !== DEFAULT_VALUE) {
  if (previousCoordinates && same(coordinates, previousCoordinates)) return;  // skip identical recompute
  this.#previousCoordinates = coordinates;
}
this.#collisions.value = collisions;

// inside computeCollisions loop:
potentialTargets.push(entry);
void entry.shape;                                   // READ to subscribe: shape changes re-run this effect
const collision = untracked(() => detectCollision({droppable: entry, dragOperation}));

// notifier.ts second effect
if (Entity.pendingIdChanges) return;                // never dispatch mid id-swap
monitor.dispatch('collision', event);               // listeners may preventDefault
if (isEqual(collisions, previousCollisions)) return;
if (firstCollision?.id !== manager.dragOperation.target?.id) {
  collisionObserver.disable();                      // KILL SWITCH
  manager.actions.setDropTarget(firstCollision?.id)
    .then(() => collisionObserver.enable());        // re-arm after dragover settles
}
```

**Flow:** effect tracks (status.initialized, source shape, every entry.shape, modifiers) → compute → coordinate-equality skip → publish. The notifier reacts to published collisions, lets listeners veto, dedupes by id-join, and — when the winner differs from the current target — disables detection, sets the target (which fires dragover AFTER rendering and resolves with defaultPrevented), then re-enables. Disabled windows swallow publishes so the setDropTarget→dragover→recompute cycle cannot feed itself.
**Invariant:** detectors run UNTRACKED (their internal reads must not subscribe); `accepts()`/disabled filters run BEFORE detection so ignored droppables consume nothing; priority from the droppable overrides the algorithm's default (`collision.priority = entry.collisionPriority`).
**Probe:** `packages/dom/tests/sortable-utilities.test.ts` covers accept plumbing neighbors; closestCenter's fallback ladder is pinned by its own algorithm contract; live probe: lifted `hasChanged` snapshot logic returns false on gapped indices unchanged, true after index mutation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "CollisionObserver", name_pattern: "^CollisionObserver$", limit: 10 });
```

## Verdict
Adopt read-to-subscribe + untracked-detector evaluation + the disable/re-enable window around target changes; adapt sort keys to your ranking vocabulary (keep priority > type > value precedence); omit the pendingIdChanges guard only if you have no atomic id swaps.
