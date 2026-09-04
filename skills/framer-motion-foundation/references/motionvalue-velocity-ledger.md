<!-- capsule-v2 -->
# MotionValue velocity ledger & passive effects — where does animation velocity come from and why does it expire?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** How must a porter track per-value velocity across frames, and what exactly do `set`/`jump`/`setWithVelocity`/`start`/`stop` do to that ledger?

## The ledger inside `MotionValue`
**Path/Symbol:** `packages/motion-dom/src/value/index.ts:MotionValue` (:84-511; velocity core :406-428, `setWithVelocity` :313-318, `updateAndNotify` :349-375, passive-effect `set` :305-311).
**Signature:** `getVelocity(): number` (units/sec); `setWithVelocity(prev: V, current: V, delta: number)`; `set(v)`; `jump(v, endAnimation=true)`.
**Data Shape:** Private fields `current/prev/prevFrameValue/updatedAt/prevUpdatedAt`. `canTrackVelocity` latched ON FIRST non-undefined setCurrent via `isFloat` — strings like `"100px"` DO track (parseFloat). Module constant `MAX_VELOCITY_DELTA = 30` (ms).

### Decisive source
```ts
setWithVelocity(prev, current, delta) {
    this.set(current); this.prev = undefined
    this.prevFrameValue = prev
    this.prevUpdatedAt = this.updatedAt - delta   // synthetic backdated sample
}
getVelocity() {
    const currentTime = time.now()
    if (!this.canTrackVelocity || this.prevFrameValue === undefined
        || currentTime - this.updatedAt > MAX_VELOCITY_DELTA) return 0
    const delta = Math.min(this.updatedAt - this.prevUpdatedAt!, MAX_VELOCITY_DELTA)
    return velocityPerSecond(parseFloat(current) - parseFloat(prevFrameValue), delta)
}
updateAndNotify = (v) => {
    if (this.updatedAt !== currentTime) this.setPrevFrameValue()  // new eventloop-frame -> roll ledger
    this.prev = this.current; this.setCurrent(v)
    if (this.current !== this.prev) { events.change?.notify(current); dependents?.forEach(d => d.dirty()) }
}
set(v) { if (!this.passiveEffect) this.updateAndNotify(v); else this.passiveEffect(v, this.updateAndNotify) }
```

**Flow:** two sets within the same `time.now()` frame roll only `current/updatedAt`; a set in a LATER frame rolls `prevFrameValue/prevUpdatedAt` first (frame-boundary ledger rotation). `getVelocity` returns 0 when the last update is >30 ms stale or the delta window exceeds 30 ms (clamp prevents huge spikes from stale samples). `jump` zeroes history (`prev=undefined`, stops animation AND passive effect). `set` routes through the attached passive effect when present — this is how `useSpring` intercepts sets so callers write raw targets while the value springs toward them. Change notifications fire only on actual inequality; dependents get `.dirty()`.
**Invariant:** Velocity is always UNITS PER SECOND (`velocityPerSecond(dx, dtMs) = dx·1000/dtMs`) even though deltas are measured in ms; forgetting the ×1000 is the classic port bug. `time.now()` (not `performance.now()`) must be used everywhere — during frameloop processing it returns the frozen frame timestamp, keeping all values in one frame consistent.
**Probe:** `packages/motion-dom/src/value/__tests__/motion-value.test.ts:26-150` — velocity zero after arbitrary creation-set, correct within one frame (two updates same frame), capped-to-window cases, `setWithVelocity` arithmetic. Behaviors live-executed GREEN with manual timing (P14/P15/P16 in `/tmp/uix-fm-p1/run2.cjs`: setWithVelocity(90→100, 40ms) ⇒ 250/s; stale>30ms ⇒ 0; 40ms gap clamped to 30ms window).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "MAX_VELOCITY_DELTA setWithVelocity getVelocity updateAndNotify", limit: 10, fields: ["signature", "name", "file"] });
```
Verified line-exact: `MotionValue.setWithVelocity` :313-318, `MotionValue.getVelocity` :406-428.

## Verdict
Adopt the four-slot time-stamped ledger, 30 ms staleness/clamp rule, frame-boundary rotation, units-per-second convention, and passive-effect interception of `set`. Adapt `canTrackVelocity` heuristics if your values aren't stringly numeric. Omit the deprecated `onChange()` method. Upstream direct tests are extensive (12 velocity scenarios); coverage clean.
