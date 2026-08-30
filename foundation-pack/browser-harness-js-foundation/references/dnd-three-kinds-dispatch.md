<!-- capsule-v2 -->
# dnd-three-kinds-dispatch — which CDP call does each kind of "drag and drop" actually need?

**Source:** browser-harness-js MIT `main@6b1894061e7a09a65a974d7d65a210b9a7ef06e0`; Codebase Memory `browser-harness-js`. **Question:** Why does mousePressed/moved/released fail on React DnD boards, and what is the exact dispatchDragEvent handshake?

## Three-kind DnD dispatch
**Path/Symbol:** `skills/cdp/interaction-skills/drag-and-drop.md` whole doc — Kind 1 (:5–28), Kind 2 (:30–45), Kind 3 (:47–49), Traps (:51–56).
**Signature:** Kind 1: `Input.setInterceptDrags({enabled:true})` → `waitFor('Input.dragIntercepted', undefined, 2_000)` → 3× `Input.dispatchDragEvent({type:'dragEnter'|'dragOver'|'drop', x, y, data: di.data})` → mouseReleased → setInterceptDrags off.
**Data Shape:** Kind 1 = HTML5 DnD (`dragstart`/`drop` DOM DragEvents: React DnD, pragmatic-drag-and-drop, native draggable) — CDP mouse events do NOT fire these because the browser synthesizes DragEvents from a NATIVE OS drag. Kind 2 = pointer-based (canvas/games/sliders listening to mousedown/move/up) — plain mouse sequence IS correct; intermediate moves matter (velocity-tracking sites no-op on a single jump). Kind 3 = "drag a file onto this zone" = actually an upload → `DOM.setFileInputFiles` (see uploads path), never fight the DnD path when a hidden input exists.

### Decisive source
```js
// Chrome needs to be told we're about to handle drags via CDP
await session.Input.setInterceptDrags({ enabled: true })
await session.Input.dispatchMouseEvent({ type: 'mousePressed', x: srcX, y: srcY, button: 'left', clickCount: 1 })
const di = await session.waitFor('Input.dragIntercepted', undefined, 2_000)
await session.Input.dispatchDragEvent({ type: 'dragEnter', x: dstX, y: dstY, data: di.data })
await session.Input.dispatchDragEvent({ type: 'dragOver',  x: dstX, y: dstY, data: di.data })
await session.Input.dispatchDragEvent({ type: 'drop',      x: dstX, y: dstY, data: di.data })
```

**Flow:** classify the listener (DragEvent vs mouse/pointer vs file drop) → route to the matching primitive → re-screenshot ~300ms post-drop (snap animations move the card after the drop).
**Invariant:** The handshake is load-bearing BOTH ways: dispatchDragEvent without setInterceptDrags(true) routes the drag to the native OS (nothing happens in-page); mouse-only sequences silently no-op HTML5 DnD ("a click that went nowhere"). If mousedown fails on new SPAs, repeat via dispatchPointerEvent with pointerType:'mouse' — some listen only to pointer events.
**Probe:** `grep -cF 'setInterceptDrags' skills/cdp/interaction-skills/drag-and-drop.md` → 4; `grep -cF "waitFor('Input.dragIntercepted', undefined, 2_000)" <same>` → 1; `grep -cF 'di.data' <same>` → 3.
**Retrieve:** search_graph --project browser-harness-js --query "setInterceptDrags dispatchDragEvent" resolves both generated.ts wrappers line-exact.

## Verdict
Adopt the classifier + the intercept→dragIntercepted→dispatchDragEvent triple as portable primitives. Adapt step counts/jitter for velocity-sensitive surfaces. Omit Kind-2 pointer emulation details if your target surface exposes semantic roles instead.
