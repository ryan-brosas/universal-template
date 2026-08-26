<!-- capsule-v2 -->
# Eight-step frameloop batcher — how does Motion guarantee read/write ordering, per-frame dedupe, and flushSync reentrancy?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** What scheduler semantics must a port reproduce so animations, layout reads, and DOM writes never interleave wrongly?

## `createRenderBatcher` + `createRenderStep`
**Path/Symbol:** `packages/motion-dom/src/frameloop/batcher.ts:createRenderBatcher` (:8-99), `frameloop/render-step.ts:createRenderStep` (:4-102), step order in `frameloop/order.ts` (:3-13). Singleton export: `frameloop/frame.ts` — `{ schedule: frame, cancel: cancelFrame, state: frameData, steps }` with rAF driver and `allowKeepAlive=true`.
**Signature:** `frame.<step>(process: Process, keepAlive = false, immediate = false)`; steps: `setup, read, resolveKeyframes, preUpdate, update, preRender, render, postRender`.
**Data Shape:** Each step owns TWO reusable `Set<Process>` queues (`thisFrame`/`nextFrame` swapped each process — GC avoidance) plus a `WeakSet` of keepAlive callbacks. FrameData `{delta, timestamp, isProcessing}`. Delta logic: first wake uses default `1000/60`; afterwards clamped to `[1, 40]` ms.

### Decisive source
```ts
// order.ts
export const stepsOrder = ["setup","read","resolveKeyframes","preUpdate","update","preRender","render","postRender"]
// batcher.ts
state.isProcessing = true
setup.process(state); read.process(state); resolveKeyframes.process(state); preUpdate.process(state)
update.process(state); preRender.process(state); render.process(state); postRender.process(state)
state.isProcessing = false
if (runNextFrame && allowKeepAlive) { useDefaultElapsed = false; scheduleNextBatch(processBatch) }
// render-step.ts
process: (frameData) => {
    if (isProcessing) { flushNextFrame = true; return }   // flushSync INSIDE a step -> defer one frame
    isProcessing = true
    const prevFrame = thisFrame; thisFrame = nextFrame; nextFrame = prevFrame
    thisFrame.forEach(triggerCallback); thisFrame.clear()   // Set dedupes same-fn schedules
    isProcessing = false
    if (flushNextFrame) { flushNextFrame = false; step.process(frameData) }
}
schedule: (callback, keepAlive = false, immediate = false) => {
    const addToCurrentFrame = immediate && isProcessing   // only DURING its own step's processing
    ;(addToCurrentFrame ? thisFrame : nextFrame).add(callback)
}
```

**Flow:** any schedule wakes the loop (`wake()` sets `runNextFrame`, schedules rAF unless already processing) → on tick, delta computed → the eight steps run UNROLLED in canonical order → a callback scheduled with `immediate=true` while its own step is mid-`process()` joins the CURRENT frame (same timestamp); otherwise it waits for next frame → keepAlive callbacks reschedule themselves inside `triggerCallback`, and a non-empty keepAlive set keeps the loop alive (`useDefaultElapsed=false` so subsequent deltas become real). Cancel removes from `nextFrame` + keepAlive only.
**Invariant:** The step ladder IS layout-safety: reads happen in `read`/`resolveKeyframes`, writes in `render` — code that writes styles inside `read` reintroduces layout thrashing no matter how correct the rest is. Same-frame dedupe relies on callers passing a STABLE function reference (Sets hold by identity). `immediate` has no effect outside the step's own processing window. `time.now()` freezes to `frameData.timestamp` while `isProcessing` — all values in one frame share one clock.
**Probe:** `packages/motion-dom/src/frameloop/__tests__/index.test.ts:4-60` — order test asserts read→update→preRender→render→postRender sequence; cancel test; immediate-in-same-step test asserting identical timestamps. Live-executed GREEN against real batcher with manual frame pump (P12/P13 in `/tmp/uix-fm-p1/run2.cjs`: order `read,update,render`; immediate lands same-timestamp).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "createRenderBatcher createRenderStep flushNextFrame toKeepAlive", limit: 10, fields: ["signature", "name", "file"] });
```
Verified line-exact: `frameloop.batcher.createRenderBatcher` :8-99.

## Verdict
Adopt the ordered multi-step batcher, dual-set queue swap, keepAlive WeakSet economics, 40 ms delta clamp, and the flushNextFrame reentrancy rule. Adapt the driver (rAF vs setTimeout vs sync test driver via `useManualTiming`) to your host. Omit the legacy frameloop shim (`frameloop/index-legacy.ts`). Upstream direct tests cover ordering/cancel/immediate; coverage clean.
