<!-- capsule-v2 -->
# Brush extent state machine — how does one component own select/move/resize brushing without tearing state?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** How are the four brush interactions (new-select, move, edge-resize, corner-resize) routed through a single class-state machine, and what does `-1` mean?

## brushingType discriminates; -1 = no selection
**Path/Symbol:** `packages/visx-brush/src/BaseBrush.tsx` (:62–729) — `handleDragStart` (:343), `handleWindowPointerMove` (:230–324), `handleBrushingTypeChange` (:555), `componentDidUpdate` resize-ratio reposition (:143–178).
**Signature:** class `BaseBrush extends Component<BaseBrushProps, BaseBrushState>`; `updateBrush(updater, cb?)` wraps setState + onChange.
**Data Shape:** `BaseBrushState = BrushShape{start,end,extent{x0,x1,y0,y1},bounds} & {activeHandle, isBrushing, brushPageOffset?, brushingType?: 'select'|'move'|'left'|'right'|'top'|'bottom'}`.

### Decisive source
```ts
// idle/empty selection sentinel — checked downstream as x0 < 0 => onChange(null)
extent: { x0: -1, x1: -1, y0: -1, y1: -1 },

// move: clamp the DELTA so the whole rect stays in bounds
const validDx = offsetX > 0
  ? Math.min(offsetX, prevBrush.bounds.x1 - x1)
  : Math.max(offsetX, prevBrush.bounds.x0 - x0);

// window-move path stores page offset at drag start, then moves RELATIVE to it
const offsetX = event.pageX - (brushPageOffset?.pageX || 0);
```

**Flow:** overlay pointer-down → `handleDragStart` sets start=end at cursor, resets extent to `-1`s, marks `isBrushing`+`brushingType:'select'` → drag-move grows extent via `getExtent(start,end)` → drag-end NORMALIZES `start/end` FROM extent corners and clears flags. Handles/corners/selection children call `handleBrushingTypeChange('left'|…|undefined)` to switch mode mid-gesture. With `useWindowMoveEvents`, listeners live on `window` (debounced move) so leaving the stage doesn't drop the gesture; page-offset math keeps relative motion across scroll.
**Invariant:** (a) `-1` sentinel means "no selection" — every consumer must treat negative extents as null; (b) `getExtent` collapses to full-width/full-height for vertical/horizontal direction modes (`brushDirection === 'vertical' ? 0 : min(...)`); (c) on container resize, existing selections SCALE by width-ratio/height-ratio instead of clearing (`componentDidUpdate` :143–178); (d) upstream quirk at :203: `Math.min(extent.y0, extent.y0)` compares y0 with itself (copy-paste; harmless because extent is already normalized by then) — preserve or fix consciously, don't cargo-cult.
**Probe:** `packages/visx-brush/test/Brush.test.tsx` (interaction flows); `test/utils.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "BaseBrush handleWindowPointerMove brushingType", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the state machine (sentinel, delta-clamping, ratio-rescale); adapt event names to your pointer stack; omit the class wrapper if porting to hooks — keep `updateBrush`'s setState-then-notify ordering.
