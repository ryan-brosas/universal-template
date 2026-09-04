<!-- capsule-v2 -->
# Sync-time clock & manual timing — why does every timestamp read go through `time.now()` instead of `performance.now()`?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** What clock contract must a port keep for frame-consistent timestamps and deterministic tests?

## Eventloop-frozen clock
**Path/Symbol:** `packages/motion-dom/src/frameloop/sync-time.ts:time` (:15-34); consumed by `MotionValue.setCurrent/getVelocity/updateAndNotify` (`value/index.ts` :178, :407, :350), `JSAnimation` (:429, :478, :488), driver `animation/drivers/frame.ts:frameloopDriver` (:9-24).
**Signature:** `time.now(): number`; `time.set(newTime)`; config flag `MotionGlobalConfig.useManualTiming`.
**Data Shape:** Module slot `now: number | undefined`, cleared in a microtask after every `set`.

### Decisive source
```ts
export const time = {
    now: (): number => {
        if (now === undefined) {
            time.set(frameData.isProcessing || MotionGlobalConfig.useManualTiming
                ? frameData.timestamp      // frozen frame clock
                : performance.now())       // live clock outside frames
        }
        return now!
    },
    set: (newTime) => { now = newTime; queueMicrotask(clearTime) },
}
// frameloopDriver.now = () => (frameData.isProcessing ? frameData.timestamp : time.now())
```

**Flow:** first read inside a synchronous context latches ONE value; the microtask clear means the next eventloop turn reads fresh. While the batcher is mid-`process()` (or manual timing is on), the latch source is `frameData.timestamp` — so a MotionValue set inside an animation callback, its passive effect, and the JSAnimation tick all share one timestamp; velocity arithmetic across them stays coherent. Outside frames it's plain `performance.now()`. Tests drive everything by setting `frameData.timestamp` + `time.set(t)` per synthetic frame (the upstream framerate test's `processFrame` helper is exactly this).
**Invariant:** Mixing raw `performance.now()` into value/velocity code breaks intra-frame consistency — two reads 1 ms apart rotate the prev-frame ledger early and halve measured velocities. The microtask (not setTimeout(0)) clear matters: promise chains within the same task still see the frozen time.
**Probe:** `packages/motion-dom/src/value/__tests__/follow-value-framerate.test.ts:beforeEach` pins the pattern (`useManualTiming=true; frameData.timestamp=0; time.set(0)`); `frameloop/__tests__/index.test.ts` exercises real processing with the same clock. Live-executed GREEN: battery P14–P16 depend on this clock through manual timing (`/tmp/uix-fm-p1/run2.cjs`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "sync-time useManualTiming frameData isProcessing", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the latch-and-microtask-clear clock and the isProcessing→frameData.timestamp rule verbatim; adapt the global-config flag name to your host. Omit nothing — 20 lines, all behavioral. Direct tests exist upstream (manual-timing suites); coverage clean.
