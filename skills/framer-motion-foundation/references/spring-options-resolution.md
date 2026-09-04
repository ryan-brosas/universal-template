<!-- capsule-v2 -->
# Spring options resolution — how do duration/bounce/visualDuration become stiffness/damping, and which option family wins?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36` (v13.1.1); Codebase Memory `ext-ui-framer-motion`. **Question:** A porter must know whether `stiffness`/`damping` or `duration`/`bounce` wins when both are supplied, what `visualDuration` compiles to, and which velocity reaches the solver.

## Options-resolution funnel (`getSpringOptions`)
**Path/Symbol:** `packages/motion-dom/src/animation/generators/spring.ts:getSpringOptions` (:171-219, with `isSpringType` :167-169 and `springDefaults` :21-48).
**Signature:** `getSpringOptions(options: SpringOptions) -> { velocity, stiffness, damping, mass, isResolvedFromDuration }`.
**Data Shape:** Defaults `{stiffness:100, damping:10, mass:1, velocity:0, duration:800ms, bounce:0.3, visualDuration:0.3s}`. Two disjoint option families: `durationKeys = ["duration","bounce"]`, `physicsKeys = ["stiffness","damping","mass"]`.

### Decisive source
```ts
let springOptions = { velocity: 0, stiffness: 100, damping: 10, mass: 1,
    isResolvedFromDuration: false, ...options }
// stiffness/damping/mass overrides duration/bounce
if (!isSpringType(options, physicsKeys) && isSpringType(options, durationKeys)) {
    // Time-defined springs should ignore inherited velocity.
    // Velocity from interrupted animations can cause findSpring()
    // to compute wildly different spring parameters ...
    springOptions.velocity = 0
    if (options.visualDuration) {
        const root = (2 * Math.PI) / (visualDuration * 1.2)
        const stiffness = root * root
        const damping = 2 * clamp(0.05, 1, 1 - (options.bounce || 0)) * Math.sqrt(stiffness)
        springOptions = { ...springOptions, mass: 1, stiffness, damping }
    } else {
        const derived = findSpring({ ...options, velocity: 0 })
        springOptions = { ...springOptions, ...derived, mass: 1 }
        springOptions.isResolvedFromDuration = true
    }
}
```

**Flow:** spread defaults → if caller supplied NO physics key AND at least one duration key → zero velocity, then either (a) `visualDuration`: closed-form conversion `root=(2π)/(visualDuration·1.2)`, `stiffness=root²`, `damping=2·clamp(0.05,1,1−bounce)·√stiffness` (mass forced to 1, flag stays false), or (b) classic `findSpring` Newton solver → `isResolvedFromDuration=true`. Any explicit physics key short-circuits the whole branch and duration/bounce are ignored entirely.
**Invariant:** Duration-derived springs MUST ignore inherited velocity — an interrupted animation carries MotionValue velocity that would otherwise flow into `findSpring()` and produce wildly different parameters (massive oscillation on small-range animations). The `velocity = 0` line is load-bearing, not cosmetic. Second invariant: duration-family resolution forces `mass: 1` so the returned stiffness/damping pair is mass-independent.
**Probe:** `packages/motion-dom/src/animation/generators/__tests__/spring.test.ts:144-159` (`withVelocity.next(100).value === withoutVelocity.next(100).value`) and `:161-192` (overshoot `< 5` even with `velocity: 5000`). Live-executed GREEN against real source via node strip-types harness (probes P03/P04, `/tmp/uix-fm-p1/run.cjs`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "findSpring approximateRoot envelope dampingRatio", limit: 10, fields: ["signature", "name", "file"] });
```
Verified line-exact: `spring.findSpring` :72-162, `spring.approximateRoot` :55-65.

## Verdict
Adopt the two-family resolution precedence (physics beats duration), the forced `velocity=0` for time-defined springs, and the `visualDuration` closed form. Adapt the `warning("spring-duration-limit")` code and unit table (duration ms, visualDuration seconds) to your host's conventions. Omit the "ported from the Framer implementation" provenance comment. Direct tests exist upstream and were live-executed; index coverage clean (`no_recorded_issue`).
