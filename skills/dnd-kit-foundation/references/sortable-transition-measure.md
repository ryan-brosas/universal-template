<!-- capsule-v2 -->
# Sortable transition measure — FLIP deltas measured only after killing transform transitions

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** Why does measuring the pre/post rect require cancelling CSS transitions first, and when does the shape cache clear?

## Sortable.animate()
**Path/Symbol:** `packages/dom/src/sortable/sortable.ts:263-335` (`animate`); trigger effect :221-233; shape-clear effect :234-243.
**Signature:** `animate(): void` — untracked body, work deferred into `manager.renderer.rendering.then(...)`; transition defaults `{duration: 250, easing: 'cubic-bezier(0.25, 1, 0.5, 1)', idle: false}`.
**Data Shape:** delta from old `droppable.shape.boundingRectangle` vs freshly measured `refreshShape()` rect; animation via `animateTransform({keyframes: {translate: [from, to]}})`.

### Decisive source
```ts
// Cancel CSS transitions on transform-related properties before measuring.
// These transitions (e.g. `transition: transform` from user CSS) would cause
// getBoundingClientRect() to return the mid-transition position rather than
// the element's final resting position, resulting in an incorrect delta.
for (const animation of element.getAnimations()) {
  if ('transitionProperty' in animation &&
      (animation.transitionProperty === 'transform' ||
       animation.transitionProperty === 'translate' ||
       animation.transitionProperty === 'scale')) {
    animation.cancel();
  }
}

const updatedShape = this.refreshShape();
const delta = {
  x: shape.boundingRectangle.left - updatedShape.boundingRectangle.left,
  y: shape.boundingRectangle.top  - updatedShape.boundingRectangle.top,
};
...
const resolvedTransition = prefersReducedMotion(getWindow(element))
  ? {...transition, duration: 0}
  : transition;
animateTransform({...}).then(() => {
  if (!manager.dragOperation.status.dragging) this.droppable.shape = undefined;
});
```

**Flow:** an index/group change re-runs the tracking effect → after the renderer commits, cancel any in-flight transform/translate/scale CSSTransitions → refresh shape (fresh DOMRectangle) → compute pixel delta old-vs-new → animate `translate` from (current + delta) to final, honoring reduced-motion as duration 0 → on completion clear the cached shape ONLY if no drag is active (mid-drag shapes feed collision detection and must persist).
**Invariant:** measurement MUST happen post-render AND post-cancel or the FLIP delta is silently wrong (the source comment is the invariant); idle-mode (`transition.idle`) is opt-in because animating reorder without an active drag surprises users; the whole body runs `untracked` so animation bookkeeping never subscribes effects.
**Probe:** upstream direct test absent for animate() itself (DOM-animation coverage caveat); neighbors pinned by `sortable-utilities.test.ts` (disabled split semantics) — port with your own visual test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "Sortable animate refreshShape", name_pattern: "^Sortable$", limit: 10 });
```

## Verdict
Adopt cancel-before-measure + reduced-motion zeroing + drag-gated shape clearing exactly; adapt keyframes/`animateTransform` to your animation util; omit idle transitions unless your UX review wants them.
