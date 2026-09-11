<!-- capsule-v2 -->
# Spring follow-value pipeline — how does a MotionValue chase a moving target without losing velocity at high frame rates?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** When the tracked source changes every frame (mouse move, scroll), how must interruption, velocity handoff, and scheduling be handled so followers don't lag behind at 240 Hz?

## Passive-effect + restart ladder
**Path/Symbol:** `packages/motion-dom/src/value/follow-value.ts:attachFollow` (:66-146; entry points `springValue`/`attachSpring` in `value/spring-value.ts:20-43` both delegate with `{type:"spring", ...options}`).
**Signature:** `attachFollow(value: MotionValue<T>, source: T | MotionValue<T>, options?: FollowValueOptions) -> VoidFunction` (cleanup).
**Data Shape:** `FollowValueOptions = Omit<ValueAnimationTransition, "onUpdate"|"onComplete"|"onPlay"|"onRepeat"|"onStop"> & { skipInitialAnimation?: boolean }`. Unit preservation: initial value `"0%"` extracts `unit="%"` via `replace(/[\d.-]/g,"")`; every write re-appends via `parseValue(v, unit)`.

### Decisive source
```ts
value.attach((v, set) => {
    latestValue = v
    latestSetter = (latest) => set(parseValue(latest, unit))
    frame.postRender(scheduleAnimation)
}, stopAnimation)

const startAnimation = () => {
    const currentValue = asNumber(value.get())
    const targetValue = asNumber(latestValue)
    if (currentValue === targetValue) { stopAnimation(); return }
    // Use the running animation's analytical velocity for accuracy,
    // falling back to the MotionValue's velocity for the initial animation.
    // This prevents systematic velocity loss at high frame rates (240hz+).
    const velocity = activeAnimation ? activeAnimation.getGeneratorVelocity() : value.getVelocity()
    stopAnimation()
    activeAnimation = new JSAnimation({ keyframes: [currentValue, targetValue], velocity,
        type: "spring", restDelta: 0.001, restSpeed: 0.01, ...options, onUpdate: latestSetter })
}
```

**Flow:** source change → passive effect stores `latestValue`, schedules ONE `frame.postRender(startAnimation)` (stable function ref ⇒ Set dedupes bursts within a frame) → start reads current vs latest, early-returns if equal → velocity handoff prefers the RUNNING animation's analytical generator velocity (`getGeneratorVelocity()`), falling back to frame-delta MotionValue velocity only for the first launch → new JSAnimation replaces old. Source-tracking branch (`isMotionValue(source)`): subscribes `source.on("change")` → `value.set(...)`; if `skipInitialAnimation === true` the FIRST change calls `value.jump(parsed, false)` instead of animating (prevents unwanted animation on page refresh/back-nav, e.g. `useScroll`+`useSpring`); cleanup unsubscribes on `value.on("destroy")`.
**Invariant:** The velocity-handoff choice is THE fix for issues #3265/#3407: restarting each frame with finite-difference velocity bleeds energy and the follower falls ~34% behind a 60 Hz run when driven at 240 Hz; analytical generator velocity makes positions frame-rate-invariant (within 10%). Rest defaults here are TIGHTER than generator defaults (`restDelta 0.001/restSpeed 0.01`). `jump()` also stops the passive effect — a jumped follower stays put.
**Probe:** `packages/motion-dom/src/value/__tests__/follow-value-framerate.test.ts` — manual-frame simulation (`processFrame` drives all 8 `frameSteps` with `useManualTiming`) asserts `pos240/pos60 ∈ (0.9, 1.1)`; `packages/motion-dom/src/value/__tests__/spring-value.test.ts:189-252` pins skipInitialAnimation jump-then-animate. Both behaviors live-executed GREEN (P17/P18 in `/tmp/uix-fm-p1/run2.cjs`; framerate parity reproduced qualitatively through manual frames).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "attachFollow followValue skipInitialAnimation parseValue", limit: 10, fields: ["signature", "name", "file"] });
```
Verified by trace_path: `springValue → followValue → attachFollow → isMotionValue/parseValue`.

## Verdict
Adopt the postRender-coalesced restart ladder, analytical-velocity handoff, unit extraction/reapplication, and the one-shot `skipInitialAnimation` jump. Adapt the React glue (`useInsertionEffect` + `JSON.stringify(options)` dep in `use-follow-value.ts`) to your framework's effect story. Omit the deprecated `value.onChange` alias path. Upstream direct tests cover framerate parity and lifecycle; coverage clean.
