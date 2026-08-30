<!-- capsule-v2 -->
# Select auto-scroll buttons — how do hover-held edge buttons scroll one item per tick, and how does the viewport grow on wheel?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** What is the mount/visibility/auto-scroll protocol of SelectScrollUp/DownButton and the expand-on-scroll behavior of the viewport?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/select/src/select.tsx:SelectScrollUpButton` (:1572-1606), `SelectScrollDownButton` (:1617-1654), `SelectScrollButtonImpl` (:1661-1712), viewport expand-on-scroll (:1250-1276).
**Signature:** visibility = derived state (`canScrollUp: viewport.scrollTop > 0`; `canScrollDown: Math.ceil(viewport.scrollTop) < scrollHeight - clientHeight`) recomputed on every scroll event; auto-scroll tick = `viewport.scrollTop ± selectedItem.offsetHeight` every 50ms.
**Data Shape:** single interval handle per button (`autoScrollTimerRef`); `onAutoScroll` injected by direction twin; impl adds `flexShrink: 0` so buttons never compress.

### Decisive source
```ts
function handleScroll() {
  const maxScroll = viewport.scrollHeight - viewport.clientHeight;
  // we use Math.ceil here because if the UI is zoomed-in
  // `scrollTop` is not always reported as an integer
  const canScrollDown = Math.ceil(viewport.scrollTop) < maxScroll;
  setCanScrollDown(canScrollDown);
}
...
onPointerDown={composeEventHandlers(props.onPointerDown, () => {
  if (autoScrollTimerRef.current === null) {
    autoTimerRef.current = window.setInterval(onAutoScroll, 50);
  }
})}
```
Viewport expansion:
```ts
const scrolledBy = Math.abs(prevScrollTopRef.current - viewport.scrollTop);
if (prevHeight < availableHeight) {
  const nextHeight = prevHeight + scrolledBy;
  const clampedNextHeight = Math.min(availableHeight, nextHeight);
  ...
  if (contentWrapper.style.bottom === '0px') {
    viewport.scrollTop = heightDiff > 0 ? heightDiff : 0;
    contentWrapper.style.justifyContent = 'flex-end';   // stay pinned to bottom
  }
}
```

**Flow:** button mounts only when scrollable in its direction (visibility itself changes layout ⇒ position() must re-run once, handled by `handleScrollButtonChange`'s shouldRepositionRef latch) → pointerdown OR pointermove starts ONE shared interval (guarded by null-check; move also calls onItemLeave so item hover doesn't fight scrolling) → pointerleave/unmount clears → wheel-scrolling inside the viewport GROWS the wrapper height by the scrolled amount up to `availableHeight`, keeping bottom-pinned content anchored via scrollTop compensation + flex-end.
**Invariant:** the Math.ceil zoom guard prevents a permanently-visible down button at fractional scrollTop; the interval singleton check prevents stacked timers from pointerdown+pointermove double-fire; expand-on-scroll must be armed ONLY after initial placement (rAF latch in the positioning capsule) or the programmatic initial scrollTop counts as user expansion.
**Probe:** byte-exact anchors: `bash -c "cd /mnt/hdd/utopia/inspo/external/ui-radix-ui && grep -cF 'window.setInterval(onAutoScroll, 50)' packages/react/select/src/select.tsx"` (=2, both directions) and `grep -nF 'Math.ceil(viewport.scrollTop)' packages/react/select/src/select.tsx"` (:1633). No isolated spec drives these (layout-dependent); verified against whole-file read at pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "SelectScrollButtonImpl onAutoScroll viewport", limit: 10 });
```

## Verdict
Adopt the visibility derivation + 50ms singleton interval + height-expansion ladder; adapt tick rate/step to your UX; omit wheel-expansion only if your menus are fixed-height by design (record it). Coverage caveat recorded: no dedicated unit spec — deterministic probes only.
