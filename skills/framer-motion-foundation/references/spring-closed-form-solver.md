<!-- capsule-v2 -->
# Spring closed-form solver — how does one generator evaluate under-, critical-, and over-damped motion with correct units and rest detection?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** What exact closed-form equations, sign conventions, and rest thresholds must a port reproduce so sampled trajectories match bit-for-bit?

## The `spring()` generator
**Path/Symbol:** `packages/motion-dom/src/animation/generators/spring.ts:spring` (:221-446; helpers `calcAngularFreq` :50-52, `approximateRoot` :55-65 — 12 fixed-point Newton iterations, initial guess `5/duration`, NaN → fall back to default stiffness/damping).
**Signature:** `spring(optionsOrVisualDuration?: ValueAnimationOptions<number> | number, bounce? = 0.3) -> KeyframeGenerator<number>` where the generator is `{ calculatedDuration, velocity(t), next(t), toString(), toTransition() }`.
**Data Shape:** Reads `keyframes[0]`/`keyframes[last]` as origin/target. Returns a MUTABLE shared `state = {done, value}` object instead of allocating per tick (deliberate GC optimization — consumers must read before calling `next` again). `calculatedDuration` is non-null ONLY for duration-resolved springs.

### Decisive source
```ts
const { ... } = getSpringOptions({ ...options, velocity: -millisecondsToSeconds(options.velocity || 0) })
const initialDelta = target - origin
const undampedAngularFreq = millisecondsToSeconds(Math.sqrt(stiffness / mass))
// Underdamped coefficients, hoisted for use in the inlined next() hot path
A = (initialVelocity + dampingRatio * undampedAngularFreq * initialDelta) / angularFreq
resolveSpring = (t) => target - envelope * (A * sin(w*t) + initialDelta * cos(w*t))
// Overdamped: freqForT = Math.min(dampedAngularFreq * t, 300)   // sinh/cosh overflow guard
state.done = Math.abs(currentVelocity) <= restSpeed && Math.abs(target - current) <= restDelta
state.value = state.done ? target : current
```

**Flow:** negate incoming velocity (MotionValue reports "motion toward", the solver integrates toward target) → pick branch by `dampingRatio < 1` (underdamped: damped sinusoid with hoisted `angularFreq/A/sinCoeff/cosCoeff`), `== 1` (critically damped: `(Δ + (v₀+ωΔ)t)e^(−ωt)`), `> 1` (overdamped: sinh/cosh pair with argument capped at 300 to avoid Infinity) → per tick compute position AND analytic velocity (shared `exp/sin/cos` values inlined in the hot path for the physics-underdamped case) → done iff BOTH `|v| ≤ restSpeed` AND `|target−current| ≤ restDelta` → snap `value` to target when done. Granular-scale rule: `|initialDelta| < 5` switches defaults to `restSpeed 0.01` / `restDelta 0.005`, else `2` / `0.5`.
**Invariant:** Units are mixed BY DESIGN and a wrong port silently breaks everything: `undampedAngularFreq` converts to per-second (`msToS(√(k/m))`), positions are in value units, but `generator.velocity(t)` returns `secondsToMilliseconds(resolveVelocity(t))` — i.e. px/ms to match MotionValue's velocity convention. The `next()` fast path exists only for `!isResolvedFromDuration && dampingRatio < 1`; all other branches route through `resolveSpring`. `toString()` pins the numeric trajectory: `"1100ms linear(0, 0.0419, 0.1493, …)"` is asserted EXACTLY upstream.
**Probe:** `packages/motion-dom/src/animation/generators/__tests__/spring.test.ts:13-25` — 25 ms-step ladder `[100, 1343, 873, 1046, 984, 1005, 998, 1001, 1000]` for `[100→1000], k=300, restSpeed=10, restDelta=0.5`; also `:194-208` zero-delta overdamped NOT immediately done; `:222-233` same-number spring settles in exactly 600 ms; `:236-251` visualDuration shorthand identity `spring({visualDuration:.5,bounce:.25}) ≡ spring(0.5, 0.25)`. All live-executed GREEN (P01R/P05/P06/P07/P08/P09/P10 in `/tmp/uix-fm-p1/run.cjs`, real source via node type-stripping).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "spring resolveSpring resolveVelocity restSpeed restDelta", limit: 10, fields: ["signature", "name", "file"] });
```
Verified: `packages.motion-dom.src.animation.generators.spring.spring` :221-446.

## Verdict
Adopt the closed forms, the velocity negation, the dual-threshold rest condition, the granular-scale threshold switch, the sinh/cosh 300-cap, and the px/ms velocity unit. Adapt default constants only with care — they are pinned by exact-string tests. Omit nothing behavioral here; the file is the contract. Upstream direct tests cover all three damping regimes; coverage clean.
