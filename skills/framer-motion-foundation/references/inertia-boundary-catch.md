<!-- capsule-v2 -->
# Inertia boundary-catch composition — how does deceleration hand off to a spring exactly once at min/max?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** How must a porter sequence friction decay and bounce springs so the boundary catch happens at the right time with the right velocity, and never twice per frame?

## Friction phase + lazy bounce spring
**Path/Symbol:** `packages/motion-dom/src/animation/generators/inertia.ts:inertia` (:6-114; velocity sampling helper `generators/utils/velocity.ts:getGeneratorVelocity` :4-10).
**Signature:** `inertia({keyframes, velocity=0, power=0.8, timeConstant=325, bounceDamping=10, bounceStiffness=500, modifyTarget?, min?, max?, restDelta=0.5, restSpeed?}) -> KeyframeGenerator<number>`.
**Data Shape:** Target derived, not given: `amplitude = power·velocity`, `ideal = origin + amplitude`, optionally remapped by `modifyTarget(ideal)` — if the target changed, `amplitude = target − origin` is recomputed or the animation starts from the wrong position.

### Decisive source
```ts
const calcDelta = (t) => -amplitude * Math.exp(-t / timeConstant)
const calcLatest = (t) => target + calcDelta(t)
const applyFriction = (t) => { const delta = calcDelta(t)
    state.done = Math.abs(delta) <= restDelta; state.value = state.done ? target : calcLatest(t) }
let timeReachedBoundary; let spring
const checkCatchBoundary = (t) => {
    if (!isOutOfBounds(state.value)) return
    timeReachedBoundary = t
    spring = createSpring({ keyframes: [state.value, nearestBoundary(state.value)!],
        velocity: getGeneratorVelocity(calcLatest, t, state.value),  // TODO: should be *1000 upstream
        damping: bounceDamping, stiffness: bounceStiffness, restDelta, restSpeed })
}
next: (t) => {
    let hasUpdatedFrame = false
    if (!spring && timeReachedBoundary === undefined) { hasUpdatedFrame = true; applyFriction(t); checkCatchBoundary(t) }
    if (timeReachedBoundary !== undefined && t >= timeReachedBoundary) return spring!.next(t - timeReachedBoundary)
    !hasUpdatedFrame && applyFriction(t)
    return state
}
```

**Flow:** exponential decay toward the power-derived target until a sample lands out of bounds → freeze `timeReachedBoundary` and build the catch spring ONCE from `[currentValue → nearestBoundary]` with velocity estimated by 5 ms finite difference of the friction curve (`getGeneratorVelocity` samples `calcLatest(max(t−5,0))`) → every later tick delegates to `spring.next(t − timeReachedBoundary)` (time rebased at the crossing). The `hasUpdatedFrame` flag guarantees friction is evaluated at most once per frame even when both the done-check and the delegation branch would call it.
**Invariant:** The spring's local clock starts at the boundary-crossing timestamp, not zero — feeding absolute t into the catch spring double-counts the friction phase. `nearestBoundary` picks whichever of min/max is closer (ties → max). Known upstream quirk: the TODO admits the sampled velocity misses the ×1000 units conversion — port the behavior as-is if you want identical feel. JSAnimation deliberately EXEMPTS inertia from final-keyframe snapping (`type !== inertia` guard in tick) because the generator itself settles on its own target.
**Probe:** `packages/motion-dom/src/animation/generators/__tests__/inertia.test.ts` (upstream suite exists; not runnable here — no installed deps). Live deterministic probe P11 GREEN: `inertia({keyframes:[0], velocity:1000})` decays monotonically toward `origin + power·velocity = 800` and reports `done` via restDelta (`/tmp/uix-fm-p1/run.cjs`). Graph retrieval: `search_graph "inertia checkCatchBoundary timeReachedBoundary"` resolves the file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "inertia modifyTarget bounceDamping nearestBoundary", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-shot boundary latch, rebased spring clock, single-eval-per-frame flag, and target-derivation math including the modifyTarget amplitude recompute. Adapt bounds semantics (undefined side = unbounded) freely. Omit nothing else — the file is small and entirely behavioral. Caveat: upstream jest suite exists but was not executable in this environment; behavior pinned by live probes against real source instead.
