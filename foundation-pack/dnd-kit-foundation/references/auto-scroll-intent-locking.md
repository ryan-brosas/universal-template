<!-- capsule-v2 -->
# Auto-scroll intent locking — direction locks unlock only after repeated confirmation

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How does auto-scroll avoid oscillating when the pointer hovers a threshold edge, and how do keyboard drags participate in scrolling?

## ScrollIntentTracker / Scroller / AutoScroller trio
**Path/Symbol:** `packages/dom/src/core/plugins/scrolling/ScrollIntent.ts:22-77` + `ScrollLock.ts:7-32` + `Scroller.ts:26-238` + `AutoScroller.ts:27-81` + speed math `utilities/scroll/detectScrollIntent.ts:29-145`.
**Signature:** `ScrollLock.isLocked(direction?)` — null asks "BOTH directions locked?"; `unlock(direction)` never re-locks (fresh ScrollIntent per drag); `Scroller.scroll({by}?, scrollOptions?): boolean` returns whether ANY container actually scrolled.
**Data Shape:** per-axis `{x,y}` locks seeded LOCKED; tracker compares consecutive drag deltas (`Math.sign(a-b)`) and unlocks matching directions inside one batch.

### Decisive source
```ts
// ScrollIntent.ts effect
const directions = { x: getDirection(delta.x, previousDelta.x),
                     y: getDirection(delta.y, previousDelta.y) };
batch(() => {
  for (const axis of Axes)
    for (const direction of DIRECTIONS)
      if (directions[axis] === direction) intent[axis].unlock(direction);
});

// Scroller.scroll(): first-match wins over scrollable ancestors
for (const scrollableElement of elements) {
  const elementCanScroll = canScroll(scrollableElement, by);
  if (elementCanScroll.x || elementCanScroll.y) {
    const {speed, direction} = detectScrollIntent(el, currentPosition,
        intent, acceleration /*25*/, threshold /*0.2 per axis*/);
    if (scrollIntent) for (const axis of Axes)
      if (scrollIntent[axis].isLocked(direction[axis])) { speed[axis]=0; direction[axis]=0; }
    if (direction.x || direction.y) { ... scheduler.schedule(this.#scroll); return true; }
  }
}

// AutoScroller: rAF-scheduled interval while dragging
const canScroll = scroller.scroll(undefined, scrollOptions);
if (canScroll) { scroller.autoScrolling = true;
  const interval = setInterval(() =>
    scheduler.schedule(() => scroller.scroll(undefined, scrollOptions)),
    AUTOSCROLL_INTERVAL /*10ms*/);
  return () => clearInterval(interval); }
```

**Flow:** every drag move updates the tracker → a direction becomes scrollable ONLY after it was observed as the delta direction (hover-jitter starts locked both ways) → Scroller walks scrollable ancestors (computed from elementFromPoint with sticky previous-element fallback), computes proximity-scaled speed (`acceleration × |distance into threshold zone| / threshold`), zeroes locked axes, scrolls the FIRST candidate that can move via one rAF-scheduled write → AutoScroller re-arms that same call on a 10ms interval for continuous auto-scroll and tears the interval down when the effect re-runs. KeyboardSensor's dragmove listener converts arrow-key moves into `scroll({by})` and PREVENTS the move when scrolling succeeded (keyboard pans the list instead of moving the item).
**Invariant:** locks are monotonic within a drag (never re-lock — reset happens only on drag start via fresh ScrollIntent); at most ONE container scrolls per tick (early return); scroll writes go through the shared scheduler so they coalesce per frame; AutoScroller throws if the Scroller plugin is missing (dependency made loud).
**Probe:** no dedicated upstream unit file for the scrolling plane (coverage caveat — DOM-timing heavy); pinned indirectly by pointer/keyboard sensor suites which execute activation paths through these plugins.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "AutoScroller Scroller", name_pattern: "^AutoScroller$", limit: 10 });
```

## Verdict
Adopt confirm-twice unlocking + single-winner scroll selection + threshold-proportional speed; adapt thresholds/acceleration defaults to your content density; omit inverted-axis handling (`scaleX/Y < 0` flips direction in detectScrollIntent) only if transforms on scroll containers are impossible in your app.
