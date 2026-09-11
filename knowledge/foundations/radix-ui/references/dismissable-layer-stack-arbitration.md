<!-- capsule-v2 -->
# DismissableLayer stack arbitration — how do N stacked overlays agree on who handles Escape and whether the body ignores pointers?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** How do layered components coordinate outside-pointer disabling, body pointer-events restoration, and Escape handling when several are open at once?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/dismissable-layer/src/dismissable-layer.tsx:DismissableLayer` (:71-246), registration effect (:177-202), unmount-only removal effect (:210-217 comment block), Escape handler (:156-175), context (:16-27).
**Signature:** `<DismissableLayer disableOutsidePointerEvents? deferPointerDownOutside? onEscapeKeyDown? onPointerDownOutside? onFocusOutside? onInteractOutside? onDismiss?>`; context holds `layers / layersWithOutsidePointerEventsDisabled / branches / dismissableSurfaces` Sets.
**Data Shape:** module-global `originalBodyPointerEvents` captured once; per-layer computed `index` (position in creation-ordered `layers`); `isPointerEventsEnabled = index >= highestLayerWithOutsidePointerEventsDisabledIndex`.

### Decisive source
```ts
React.useEffect(() => {
  if (!node) return;
  if (disableOutsidePointerEvents) {
    if (context.layersWithOutsidePointerEventsDisabled.size === 0) {
      originalBodyPointerEvents = ownerDocument.body.style.pointerEvents;
      ownerDocument.body.style.pointerEvents = 'none';
    }
    context.layersWithOutsidePointerEventsDisabled.add(node);
  }
  ...
  return () => {
    // Remove from disabled set whenever disableOutsidePointerEvents becomes
    // false (modal closes but stays mounted during exit animation), not only
    // on unmount. Otherwise body could stay pointer-events:none with multiple
    // overlapping layers. (#3645)
    if (disableOutsidePointerEvents) {
      context.layersWithOutsidePointerEventsDisabled.delete(node);
      if (context.layersWithOutsidePointerEventsDisabled.size === 0) {
        ownerDocument.body.style.pointerEvents = originalBodyPointerEvents;
      }
    }
  };
}, [node, ownerDocument, disableOutsidePointerEvents, context]);
```
(separate effect removes from `layers` ONLY on unmount — combining them would reorder creation order on every prop flip)

**Flow:** mount appends node to `layers` (+disabled set when requested), dispatches `dismissableLayer.update` so peers re-render their indices → style computes `pointer-events: auto` iff this layer is at-or-above the topmost pointer-disabling layer → Escape: EVERY layer registers a capture keydown listener but the handler body early-returns unless `isHighestLayer`, then runs cancelable `onEscapeKeyDown` before `preventDefault()+onDismiss()` → unmount deletes from both sets + broadcasts update. Handler stability uses useCallbackRef instead of useEffectEvent because React 19.2's useEffectEvent returns stale closures inside forwardRef (#4014).
**Invariant:** the two effects MUST remain separate — a `disableOutsidePointerEvents` flip would otherwise remove+re-add the node to `layers` and corrupt creation order; body restore fires on prop flip AND on last-disabled-unmount; Escape is handled by exactly one layer regardless of how many listen.
**Probe:** direct tests `packages/react/dismissable-layer/src/dismissable-layer.test.tsx` :68-280 (outside/inside/prevented/focus/branch/defer/shadow cases). Byte-exact anchor: `bash -c "cd $REFERENCE_ROOT/external/ui-radix-ui && grep -nF 'We purposefully prevent combining this effect' packages/react/dismissable-layer/src/dismissable-layer.tsx"` (:205).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "usePointerDownOutside defer pointer down outside", limit: 10 });
```

## Verdict
Adopt the set-based stack + index comparison + split-effect discipline as-is; adapt the CustomEvent names and discrete dispatch to your event bus; omit `deferPointerDownOutside` only if your host has no touch devices or extension stopPropagation conflicts (then record why). Direct upstream tests cover the matrix at this pin.
