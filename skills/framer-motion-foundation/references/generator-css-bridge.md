<!-- capsule-v2 -->
# Generator-to-CSS bridge — how does a physics spring become a WAAPI-playable `linear()` easing string, and what is `spring.applyToOptions` for?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** How must a port convert an unbounded-time generator into fixed-duration CSS/WAAPI output without changing the feel?

## Duration sampling + `applyToOptions` rewrite
**Path/Symbol:** `packages/motion-dom/src/animation/generators/spring.ts:spring.toString` (:427-441) and `spring.applyToOptions` (:448-455); helpers `generators/utils/calc-duration.ts:calcGeneratorDuration` (:6-19, `maxGeneratorDuration = 20_000`) and `generators/utils/create-generator-easing.ts:createGeneratorEasing` (:7-22); string builder `animation/waapi/utils/linear.ts:generateLinearEasing` (:4-17).
**Signature:** `calcGeneratorDuration(generator) -> number (ms | Infinity)`; `createGeneratorEasing(options, scale=100, createGenerator) -> {type:"keyframes", ease(progress), duration(seconds)}`; `generateLinearEasing(easing, durationMs, resolution=10) -> "linear(p1, p2, …)"`.
**Data Shape:** Sampling ladder steps 50 ms up to the 20 s practical cap; exceeding it returns `Infinity`. Points rounded to 4 decimals; point count `max(round(duration/resolution), 2)`.

### Decisive source
```ts
// calc-duration.ts — stop when the generator reports done
let duration = 0; const timeStep = 50
let state = generator.next(duration)
while (!state.done && duration < maxGeneratorDuration) { duration += timeStep; state = generator.next(duration) }
return duration >= maxGeneratorDuration ? Infinity : duration

// spring.applyToOptions — rewrite a spring transition into a keyframes transition
spring.applyToOptions = (options: Transition) => {
    const generatorOptions = createGeneratorEasing(options as any, 100, spring)
    options.ease = generatorOptions.ease
    options.duration = secondsToMilliseconds(generatorOptions.duration)
    options.type = "keyframes"      // <- type MUTATED in place; downstream plays a tween
    return options
}
```

**Flow:** to flatten a spring for WAAPI/CSS: measure settle time by stepping the generator at 50 ms until done (cap 20 s) → build an easing function that re-samples the generator across `[0, duration]` normalized to progress → serialize as `linear(0.0419, 0.1493, …)` with per-point rounding → emit `"1100ms linear(...)"`. `applyToOptions` is the handoff used by renderers that cannot run JS generators: it replaces `type:"spring"` with an equivalent pre-baked keyframes tween IN PLACE (mutating the caller's transition object).
**Invariant:** The scale-100 trick matters: generators animate arbitrary units, easings map progress→progress, so the probe generator runs on synthetic keyframes `[0, scale]` and divides by `scale` — reuse it verbatim or overshoot magnitudes distort. A spring whose rest condition never fires yields `Infinity` duration and MUST be rejected before serialization (upstream clamps with `Math.min(calcGeneratorDuration(generator), maxGeneratorDuration)`). The exact serialized string is pinned byte-for-byte by tests — rounding or resolution changes break them.
**Probe:** `packages/motion-dom/src/animation/generators/__tests__/spring.test.ts:254-287` — three exact `toString()` strings (physics default, `duration:800/bounce:.25`, visualDuration .5). Live-executed GREEN (P09 prefix/suffix + P08 shorthand identity, `/tmp/uix-fm-p1/run.cjs`). Same machinery drives WAAPI output in `animation/waapi/` and NativeAnimation classes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "generateLinearEasing createGeneratorEasing calcGeneratorDuration applyToOptions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 50 ms ladder + 20 s cap + scale-100 normalization + linear() serialization pipeline and the in-place type rewrite contract of applyToOptions. Adapt resolution (10 ms default) only if your target tolerates larger easing strings. Omit the Framer-provenance comment. Upstream exact-string tests are the direct tests; live-executed green here.
