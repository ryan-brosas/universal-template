<!-- capsule-v2 -->
# Droppable shape lifecycle — observation windows and the PositionObserver visibility machine

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** When does a droppable's shape get measured, refreshed during a drag, and cleared — and how is "moved without DOM mutation" detected?

## DOM Droppable + PositionObserver
**Path/Symbol:** `packages/dom/src/core/entities/droppable/droppable.ts:22-122` + `packages/dom/src/utilities/observers/PositionObserver.ts:18-188`.
**Signature:** `updateShape(rect?)` writes a `DOMRectangle` unless `shape.equals(updated)`; observation gate `observePosition = source && status.initialized && element && !disabled && accepts(source)`; `refreshShape()` public re-measure.
**Data Shape:** `PositionObserver` = IntersectionObserver (visibility, 0..1 thresholds ×100) + inner IntersectionObserver with computed rootMargin inset (position tracking) + ResizeNotifier, throttled at `THROTTLE_INTERVAL=75`.

### Decisive source
```ts
// droppable.ts — three cooperating effects:
() => {   // gate: observe only eligible droppables DURING an initialized drag
  observePosition.value = Boolean(source && dragOperation.status.initialized &&
    element && !this.disabled && this.accepts(source));
},
() => {   // observe while gated; teardown clears the cached shape
  if (observePosition.value && element) {
    const positionObserver = new PositionObserver(element, updateShape);
    return () => { positionObserver.disconnect(); this.shape = undefined; };
  }
},
() => {   // any droppable present at drop end clears its shape
  if (this.manager?.dragOperation.status.initialized) {
    return () => { this.shape = undefined; };
  }
},

// PositionObserver — moved-without-mutation detector (scroll of an ancestor)
const intersectionRatio = entry.intersectionRatio !== 1
  ? entry.intersectionRatio
  : Rectangle.intersectionRatio(intersectionRect, getVisibleBoundingRectangle(element));
if (intersectionRatio !== 1) this.#observePosition();   // keep chasing until fully visible again
```

**Flow:** drag initializes → eligible droppables arm observers → any position/size change re-measures into `shape` (deduped by Shape.equals so identical rects don't publish) → drag ends/cancel → effects tear down and null every shape. The observer's rootMargin trick expands an IntersectionObserver to exactly the element's visible rect so ancestor scrolling shows up as ratio drift even though nothing in the DOM mutated.
**Invariant:** shapes exist ONLY within a drag window (collision code may assume freshness); `element` getter prefers `proxy ?? #element`, which is what makes placeholders transparent to hit-testing; hidden elements (`callback(null)`) clear rather than freeze stale geometry.
**Probe:** no dedicated unit file for the observer trio (DOM-observer coverage caveat); consumers exercised via sortable suites in integration stories.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "PositionObserver", name_pattern: "^PositionObserver$", limit: 10 });
```

## Verdict
Adopt the eligibility-gated observation window and clear-on-teardown shape discipline; adapt the IO-threshold chase to platforms where IntersectionObserver is unavailable (fall back to scroll/resize listeners); omit proxy indirection if you never clone sources.
