<!-- capsule-v2 -->
# JSAnimation playback machine — how do repeat modes, delay, pause/hold, speed reversal, and final-keyframe snapping compose over one generator?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** What time-arithmetic invariants must a port keep so springs/inertia/keyframes all behave identically across play/pause/reverse/repeat?

## `tick()` as the single sampling point
**Path/Symbol:** `packages/motion-dom/src/animation/JSAnimation.ts:JSAnimation.tick` (:189-351; init :101-172; velocity accessor :404-419; play/pause :439-480).
**Signature:** `new JSAnimation(options: ValueAnimationOptions<T>)` autoplays unless `autoplay:false`; `tick(timestamp, sample=false)`; `getGeneratorVelocity(): number`.
**Data Shape:** Durations triple: `calculatedDuration` (generator's own, cached ON the generator object so timeline resolvers can reuse it), `resolvedDuration = calculatedDuration + repeatDelay`, `totalDuration = resolvedDuration·(repeat+1) − repeatDelay`. State field: `"idle"|"running"|"paused"|"finished"`.

### Decisive source
```ts
if (this.state === "finished" && this.holdTime === null) this.currentTime = totalDuration
if (repeat) {
    const progress = Math.min(this.currentTime, totalDuration) / resolvedDuration
    let currentIteration = Math.floor(progress)
    let iterationProgress = progress % 1.0
    if (!iterationProgress && progress >= 1) iterationProgress = 1
    iterationProgress === 1 && currentIteration--
    currentIteration = Math.min(currentIteration, repeat + 1)
    const isOddIteration = Boolean(currentIteration % 2)
    if (isOddIteration) {
        if (repeatType === "reverse") { iterationProgress = 1 - iterationProgress
            if (repeatDelay) iterationProgress -= repeatDelay / resolvedDuration }
        else if (repeatType === "mirror") frameGenerator = mirroredGenerator!
    }
    elapsed = clamp(0, 1, iterationProgress) * resolvedDuration
}
if (isInDelayPhase) { this.delayState.value = keyframes[0]; state = this.delayState }  // reusable obj
...
if (isAnimationFinished && type !== inertia)
    state.value = getFinalKeyframe(keyframes, this.options, finalKeyframe, this.speed)
```

**Flow:** constructor runs `initAnimation()` (type defaults to keyframes generator; dev invariant "Only two keyframes currently supported with spring and inertia animations"; NON-NUMERIC first keyframe + generator ⇒ bridge: keyframes replaced by `[0,100]` and a `pipe(percentToProgress, mix(kf0, kf1))` mixer applied post-sample — this is HOW `"0%"→"100%"` springs work; mirror repeats pre-build a SECOND generator with reversed keyframes and negated velocity rather than reversing time) → driver feeds rAF timestamps into `tick` → delay phase replays keyframes[0] from a reused state object → repeat arithmetic maps wall time onto iteration-local `elapsed` → finished animations snap value via `getFinalKeyframe` (first keyframe when `speed < 0` OR odd count of non-loop repeats; else last non-null) EXCEPT inertia (its own boundary spring already holds the resting value). Pause = `holdTime` latch; reverse playback rebases `startTime` off `totalDuration/speed`; `sample(t)` forces `startTime=0` for scrubbing/timelines.
**Invariant:** Timestamps can arrive BELOW `performance.now()`-derived startTime — `tick` clamps `startTime = Math.min(startTime, timestamp)` (forward) or against `timestamp − totalDuration/speed` (reverse), else negative elapsed corrupts iteration math. Floating-point subtraction noise is handled by ROUNDING animationTime (`Math.round(timestamp − startTime)`). `getGeneratorVelocity` prefers the generator's analytical `velocity(t)` (springs) and only falls back to 5 ms finite-difference for generators without one.
**Probe:** `packages/motion-dom/src/value/__tests__/spring-value.test.ts:260-318` (isAnimating true during run, animationComplete fires, false after) exercise start/stop/complete through JSAnimation; `spring.test.ts` toString pins duration computation. Non-numeric bridge + getFinalKeyframe matrix live-executed GREEN (P19/P20 in `/tmp/uix-fm-p1/run2.cjs`). Full jest suite NOT run (inspo clone has no installed workspace deps) — recorded as runner block, deterministic probes substitute.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "JSAnimation tick mirroredGenerator holdTime mixKeyframes", limit: 10, fields: ["signature", "name", "file"] });
```
Verified: class resolves at `packages/motion-dom/src/animation/JSAnimation.ts`.

## Verdict
Adopt the three-duration algebra, iteration parity rules (reverse adjusts repeatDelay; mirror swaps generators), delay-phase initial-keyframe replay, timestamp clamps/rounding, and the inertia exception in final-keyframe snapping. Adapt the WAAPI twin (`NativeAnimation*` classes wrap the same contracts natively) only if you target native playback. Omit legacy `animateValue` alias. Upstream tests cover lifecycle through follow-value suites; coverage clean.
