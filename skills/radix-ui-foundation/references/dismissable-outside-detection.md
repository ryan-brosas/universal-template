<!-- capsule-v2 -->
# DismissableLayer outside detection — how do you reliably detect "clicked/focused outside" across React trees, shadow DOM, touch, and event-stopping extensions?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** What is the full sentinel/listener protocol that decides an interaction was outside the React subtree, and when must dismissal wait for the click?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/dismissable-layer/src/dismissable-layer.tsx:usePointerDownOutside` (:308-494), `useFocusOutside` (:500-524), `handleAndDispatchCustomEvent` (:531-546).
**Signature:** `usePointerDownOutside(handler, {ownerDocument?, deferPointerDownOutside, isDeferredPointerDownOutsideRef, dismissableSurfaces, shouldHandlePointerDownOutside?}) → { onPointerDownCapture }`.
**Data Shape:** refs: `isPointerInsideReactTreeRef` (set true in capture phase on the layer node itself — tracks the REACT tree, not DOM ancestry), `isPointerDownOutsideRef`, per-event-type interception Map ledger, stable `handleClickRef` holding the pending deferred dispatcher.

### Decisive source
```ts
const handlePointerDown = (event: PointerEvent) => {
  if (event.target && !isPointerInsideReactTreeRef.current) {
    if (!shouldHandlePointerDownOutside(event.target)) { /* branch hit ⇒ reset */ }
    isPointerDownOutsideRef.current = true;
    isDeferredPointerDownOutsideRef.current = deferPointerDownOutside && event.button === 0;
    ...
    if (!deferPointerDownOutside || event.button !== 0) {
      handleAndDispatchPointerDownOutsideEvent();
    } else {
      ownerDocument.removeEventListener('click', handleClickRef.current);
      handleClickRef.current = handleAndDispatchPointerDownOutsideEvent;
      ownerDocument.addEventListener('click', handleClickRef.current, { once: true });
    }
  }
};
const timerId = window.setTimeout(() => {
  ownerDocument.addEventListener('pointerdown', handlePointerDown);
}, 0);
```
Six interaction events (`pointerup mousedown mouseup touchstart touchend click`) each get a CAPTURE recorder + BUBBLE checker; any bubble-phase sighting means third-party code stopped propagation ⇒ that event type marks intercepted.

**Flow:** opener's own pointerdown would self-dismiss ⇒ document listener registered inside setTimeout(0) → outside down: mark, decide immediate vs deferred (primary-button + defer flag only) → non-primary buttons dispatch immediately (no reliable click to await) → deferred path waits for `click`; if ANY of the six events never reached bubble phase it was stopped ⇒ intercept ledger cancels dismissal; click missing entirely (scrolled/dragged/long-press) auto-cancels because the once-listener never fired and is re-removed continuously → shadow-DOM retargeting defeated by checking `event.composedPath().includes(content)` at the select-content call site.
**Invariant:** the inside/outside decision is made on POINTERDOWN but dispatched after CLICK resolution — porters who dispatch on pointerdown break touch (350ms browser delay can execute prevented events) and break stopPropagation-based cancel affordances (#2055/#2171); branches (menu anchors living outside the layer) must be excluded via `shouldHandlePointerDownOutside`.
**Probe:** direct tests `packages/react/dismissable-layer/src/dismissable-layer.test.tsx` — `defers touch pointer down outside dismissal until click` (:173), `dismisses immediately on non-primary mouse pointer down outside` (:187), `cancels pending touch outside dismissal when pointer down moves back inside` (:209), `treats a shadow tree inside the layer as inside` (:222), `dismisses when a later outside interaction event is stopped by default` (:245). Byte-exact anchor: `bash -c "cd /mnt/hdd/utopia/inspo/external/ui-radix-ui && grep -nF \"      'touchend',\" packages/react/dismissable-layer/src/dismissable-layer.tsx"` (:447).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "usePointerDownOutside deferPointerDownOutside click", limit: 10 });
```

## Verdict
Adopt the whole sentinel protocol including the setTimeout(0) registration and six-event ledger — every piece cancels a real failure mode documented in-repo; adapt event names if targeting pointer-event-less browsers; omit the defer path only with the recorded caveat above. Strongest test coverage of any capsule here (five named scenarios at this pin).
