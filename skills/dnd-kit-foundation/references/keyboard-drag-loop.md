<!-- capsule-v2 -->
# Keyboard drag — accessible operation loop with auto-scroll suppression and Shift speed-up

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How does a keyboard-driven drag move items, page the viewport, and end without leaving focus or scroll state broken?

## KeyboardSensor
**Path/Symbol:** `packages/dom/src/core/sensors/keyboard/KeyboardSensor.ts:57-301` (+ key normalization `KeyboardSensor.helpers.ts:47-67`).
**Signature:** defaults `offset = 10` px; codes `{start:['Space','Enter'], cancel:['Escape'], end:['Space','Enter','Tab'], up/down/left/right: arrows}`; `handleMove(direction, event)` multiplies by `event.shiftKey ? 5 : 1`.
**Data Shape:** moves are RELATIVE (`actions.move({by})`) from the element-center start coordinates; key normalization maps `' '`/`'Spacebar'`→space, `KeyA`→a, `Digit1`→1 before matching.

### Decisive source
```ts
protected handleStart(event, source, options) {
  ...
  scrollIntoViewIfNeeded(element);                    // item must be visible first
  const {center} = new DOMRectangle(element);
  const controller = this.manager.actions.start({event,
    coordinates: {x: center.x, y: center.y}, source});
  if (controller.signal.aborted) return this.cleanup();
  this.sideEffects();                                 // disable AutoScroller for the op
  ...document-level capture keydown listener...
}

private sideEffects() {
  const autoScroller = this.manager.registry.plugins.get(AutoScroller as any);
  if (autoScroller?.disabled === false) {
    autoScroller.disable();
    this.#cleanupFunctions.push(() => autoScroller.enable());   // restore on end
  }
}

// Scroller's own dragmove listener (keyboard-only branch):
if (... !isKeyboardEvent(manager.dragOperation.activatorEvent) || !event.by) return;
if (this.scroll({by: event.by})) { event.preventDefault(); }    // arrow = pan viewport
```

**Flow:** Space/Enter on the activator → preventDefault + stopImmediatePropagation → scroll item into view → start at center coordinates → temporarily disable AutoScroller → capture-phase document keydown routes arrows to relative moves and Escape/Tab/Enter/Special to end/cancel. Arrow moves ALSO reach the Scroller plugin whose keyboard-branch converts each by-delta into an actual ancestor scroll and PREVENTS the position change when scrolling succeeded — so arrows pan the container; holding Shift multiplies the step ×5.
**Invariant:** AutoScroller must be disabled for keyboard ops (pointer-position-based auto-scroll is meaningless and would fight arrow panning) and restored exactly once via cleanup list; Tab ends (focus traversal must stay usable); every handled key calls preventDefault or native page-scroll fires instead.
**Probe:** `packages/dom/tests/keyboard-sensor.test.ts` (upstream suite executed GREEN in probe run); key normalization covered indirectly through start-code matching.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "KeyboardSensor", name_pattern: "^KeyboardSensor$", limit: 10 });
```

## Verdict
Adopt the code table + Shift×5 + auto-scroll suppression trio; adapt offset/speeds to your layout density; omit scrollIntoViewIfNeeded only if activators are guaranteed on-screen.
