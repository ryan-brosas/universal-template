<!-- capsule-v2 -->
# Select item-aligned positioning — how do you align a menu to the trigger's SELECTED ITEM instead of the trigger itself, and size it to the viewport?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** How does `position="item-aligned"` compute wrapper geometry so the selected item sits over the trigger's middle, with viewport clamping and scroll-button repositioning?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/select/src/select.tsx:SelectItemAlignedPosition` (:935-1148), position callback (:950-1092), `SelectViewport` onScroll expansion (:1250-1276), `handleScrollButtonChange` (:1106-1115).
**Signature:** `position(): void` — pure DOM-geometry write into `contentWrapper.style`; runs in `useLayoutEffect(() => position(), [position])`.
**Data Shape:** requires ALL of `{trigger, valueNode, contentWrapper, content, viewport, selectedItem, selectedItemText}` before computing; module constant `CONTENT_MARGIN = 10`; reads computed styles for border/padding of content + viewport; writes `left|right`, `minWidth`, `top|bottom`, `height`, `margin`, `minHeight`, `maxHeight`.

### Decisive source
```ts
const minContentHeight = Math.min(selectedItem.offsetHeight * 5, fullContentHeight);
...
const topEdgeToTriggerMiddle = triggerRect.top + triggerRect.height / 2 - CONTENT_MARGIN;
...
const willAlignWithoutTopOverflow = contentTopToItemMiddle <= topEdgeToTriggerMiddle;
if (willAlignWithoutTopOverflow) {
  const isLastItem = items.length > 0 && selectedItem === items[items.length - 1]!.ref.current;
  contentWrapper.style.bottom = 0 + 'px';
  ...
} else {
  contentWrapper.style.top = 0 + 'px';
  ...
  viewport.scrollTop = contentTopToItemMiddle - topEdgeToTriggerMiddle + viewport.offsetTop;
}
```

**Flow:** horizontal pass mirrors the trigger width: LTR computes `itemTextOffset = itemTextRect.left - contentRect.left`, sets `minContentWidth = triggerRect.width + leftDelta` where `leftDelta = triggerRect.left - (valueNodeRect.left - itemTextOffset)`; RTL mirrors via right edges. Clamp with `clamp(left, [CONTENT_MARGIN, Math.max(CONTENT_MARGIN, rightEdge - contentWidth)])`. Vertical: fullContentHeight = borders+padding+viewport.scrollHeight; align selected-item middle to trigger middle; choose top-anchored or bottom-anchored branch by whether alignment would overflow the top; bottom branch pins `justifyContent:'flex-end'` on later expansions. `onPlaced()` then arms `shouldExpandOnScrollRef` inside `requestAnimationFrame`.
**Invariant:** the wrapper must carry `boxSizing:'border-box'` (height includes borders) and the viewport `position:relative` so `selectedItem.offsetTop` is measured relative to viewport, NOT including the flow-mounted scroll-up button; initial scroll adjustment must NOT trigger expand-on-scroll, hence the rAF arming latch. A ported version that skips `Math.max(minContentWidth, contentWidth)` collapses wide menus to trigger width.
**Probe:** `bash -c "cd /mnt/hdd/utopia/inspo/external/ui-radix-ui && grep -nF 'selectedItem.offsetHeight * 5' packages/react/select/src/select.tsx"` (:1022 five-item floor) and `grep -nF 'requestAnimationFrame' packages/react/select/src/select.tsx` (:1079 arm-after-place).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "SelectItemAlignedPosition position trigger alignment", limit: 10 });
```

## Verdict
Adopt the geometry ladder (mirror-trigger-width, five-item floor, two vertical branches, rAF arm latch); adapt constants (`CONTENT_MARGIN`) and clamp policy to your design system; omit the RTL branch only if your host never renders RTL (record it). No dedicated unit spec drives this component upstream (jsdom cannot measure layout) — verified against whole-file source read at the pin.
