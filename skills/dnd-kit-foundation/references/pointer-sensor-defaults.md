<!-- capsule-v2 -->
# Pointer sensor defaults — the activation matrix and pointer-capture choreography

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** Which input gets which activation constraints by default, and what listener/capture setup must surround an activated drag?

## PointerSensor
**Path/Symbol:** `packages/dom/src/core/sensors/pointer/PointerSensor.ts:44-87` (frozen defaults) + bind/handleStart :137-376.
**Signature:** options `{activationConstraints?: constraints | (event, source) => constraints|undefined, activatorElements?: Element[] | (source) => Element[], preventActivation?: (event, source) => boolean}`; `static configure` for descriptors.
**Data Shape:** coordinates pass through `getFrameTransform(source.element)` (`x*scaleX + offset`) so iframe/scaled containers report kernel-space positions.

### Decisive source
```ts
const defaults = Object.freeze<PointerSensorOptions>({
  activationConstraints(event, source) {
    const {pointerType, target} = event;
    if (pointerType === 'mouse' &&
        (source.handle === target || source.handle?.contains(target))) {
      return undefined;                                  // handle drag: immediate
    }
    if (pointerType === 'touch') {
      return [new Delay({value: 250, tolerance: 5})];    // long-press, 5px wiggle room
    }
    if (isTextInput(target) && !event.defaultPrevented) {
      return [new Delay({value: 200, tolerance: 0})];    // text selection first, zero movement
    }
    return [new Delay({value: 200, tolerance: 10}),
            new Distance({value: 5})];                   // EITHER gate activates
  },
  preventActivation(event, source) { /* true when target sits inside ANOTHER interactive element */ },
});

// after activation:
const pointerCaptureTarget = ownerDocument.body;
try { pointerCaptureTarget.setPointerCapture(event.pointerId); }
catch { this.handleCancel(event); return; }              // capture loss cancels cleanly

// window-level one-time patch so touch scrolling never wins over a started drag
window.addEventListener('touchmove', noop, {capture: false, passive: false});
```

**Flow:** pointerdown (primary button only, not captured by another sensor, manager idle) → build ActivationController from resolved constraints → moves feed constraints until activation → handleStart calls actions.start, captures the pointer ON THE BODY (not the element — survives re-renders/reparenting), binds document-level touchmove-prevent (non-passive), click/contextmenu suppressors, and Escape-cancel. Moves while dragging are throttled through the shared scheduler (`latest` state + scheduled apply). pointerup stops with `canceled = !status.initialized` (a cancel before promotion reads as canceled).
**Invariant:** constraint resolution is per-EVENT (a function can inspect target/pointerType); `isCapturedBySensor` checks `'sensor' in event` to ignore synthetic re-dispatch from a sibling sensor; the non-passive touchmove noop must exist at WINDOW level BEFORE drag start or iOS scrolls anyway (WeakSet-deduped patch).
**Probe:** `packages/dom/tests/pointer-sensor.test.ts` (delay matrix) + `keyboard-sensor.test.ts` for the sibling path; capture/touchmove wiring is DOM-heavy (partial coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "PointerSensor", name_pattern: "^PointerSensor$", limit: 10 });
```

## Verdict
Adopt the default constraint table verbatim — it encodes years of platform quirks; adapt frame-transform math to your coordinate space; omit body-pointer-capture only if your framework never reparents mid-drag (sortable does).
