<!-- capsule-v2 -->
# Derived-value graph — how do transform/map/computed MotionValues subscribe, dedupe updates, and auto-discover dependencies?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** What mechanism wires an output value to its inputs without explicit dependency lists, and when do updates run?

## Dependency auto-collection + preRender scheduling
**Path/Symbol:** `packages/motion-dom/src/value/transform-value.ts:transformValue` (:21-43); `value/map-value.ts:mapValue` (:63-67); `value/subscribe-value.ts:subscribeValue` (:4-19); collection hook `value/index.ts:collectMotionValues` (:75-77, consumed by `get()` :384-390).
**Signature:** `transformValue<O>(transform: () => O) -> MotionValue<O>`; `mapValue(input: MotionValue<number>, inputRange: number[], outputRange: O[], options?) -> MotionValue<O>`; `subscribeValue(inputs, output, getLatest)`.
**Data Shape:** Module-level mutable session slot: `collectMotionValues.current: MotionValue[] | undefined`. Range mapping uses `utils/interpolate.ts:interpolate` (:44-113).

### Decisive source
```ts
// transform-value.ts — open session, run transformer once, close session
collectMotionValues.current = collectedValues
const initialValue = transform()
collectMotionValues.current = undefined
const value = motionValue(initialValue)
subscribeValue(collectedValues, value, transform)

// subscribe-value.ts — schedule ONE update per frame regardless of input count
const update = () => outputValue.set(getLatest())
const scheduleUpdate = () => frame.preRender(update, false, true)   // immediate=true
const subscriptions = inputValues.map((v) => v.on("change", scheduleUpdate))
outputValue.on("destroy", () => { subscriptions.forEach(u => u()); cancelFrame(update) })

// interpolate.ts — descending ranges normalized by reversing BOTH arrays
if (input[0] > input[inputLength - 1]) { input = [...input].reverse(); output = [...output].reverse() }
return isClamp ? (v) => interpolator(clamp(input[0], input[inputLength - 1], v)) : interpolator
```

**Flow:** first evaluation runs inside an open collection session; every `.get()` during it registers the source (this is the whole dependency system — no proxies, no tracking flags beyond one array slot) → each input change schedules `frame.preRender(update, false, true)`; Set-dedupe means N changing inputs still yield ONE recompute per frame, executed at the preRender step (after reads, before render writes) → destroy tears down subscriptions AND cancels any pending frame callback. React twins: `useComputed` mirrors the session trick across render, then `useCombineMotionValues` re-subscribes every effect pass (no dep array — intentional); `useTransform` maps overload matrix onto list/map transforms and propagates scroll-timeline `accelerate` config for native WAAPI promotion.
**Invariant:** Transformer functions must be PURE and unconditional — conditional `.get()` calls change the collected set between evaluations, silently dropping subscriptions. Updates land in `preRender`, never synchronously inside the input change: within one frame, ordering between producer and consumer writes is guaranteed by the frameloop ladder, not by subscription order. Interpolate clamps BY DEFAULT (`clamp !== false` opts out), requires equal-length ranges (dev invariant "range-length"), short-circuits constant outputs, and normalizes descending inputs by reversing pairs.
**Probe:** `packages/motion-dom/src/value/__tests__/transform-value.test.ts` + `map-value.test.ts` (upstream suites; runner blocked — deps absent). Live-executed GREEN against real interpolate: descending range `[200,0]→[0,1]` maps 100→0.5, clamped outside (P21 `/tmp/uix-fm-p1/run2.cjs`); mapValue/transformValue exercised transitively by follow-value unit tests (P17).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "collectMotionValues transformValue subscribeValue interpolate clamp", limit: 10, fields: ["signature", "name", "file"] });
```
Verified line-exact via search_graph (`interpolate`, `subscribeValue` resolve with spans).

## Verdict
Adopt session-scoped dependency collection, per-frame coalesced preRender updates, destroy-time teardown, and descending-range normalization with default clamping. Adapt the React hooks' re-subscribe-every-effect strategy if your framework has cheaper invalidation. Omit the `accelerate` scroll-timeline promotion metadata unless you implement native WAAPI output. Coverage caveat: upstream vitest suites exist but could not run here; pinned by live deterministic probes.
