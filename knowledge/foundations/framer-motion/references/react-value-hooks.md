<!-- capsule-v2 -->
# React value hooks wiring — which effects own subscriptions, why insertion-effect timing, and what static mode changes?

**Source:** framer-motion (Motion) MIT `main@1b037b0032578b52af94b06ff3920bfa0aaa5e36`; Codebase Memory `ext-ui-framer-motion`. **Question:** Where do subscription lifecycles live in the React layer so values survive StrictMode double-render but never leak listeners?

## Hook stack
**Path/Symbol:** `packages/framer-motion/src/value/use-follow-value.ts:useFollowValue` (:48-76); `value/use-combine-values.ts:useCombineMotionValues` (:9-41); `value/use-computed.ts:useComputed` (:6-24); `value/use-motion-value.ts:useMotionValue` (:21-40); `value/use-velocity.ts:useVelocity` (:16-33).
**Signature:** `useSpring(source, options?) -> useFollowValue(source, {type:"spring", ...options})`; `useVelocity(value) -> MotionValue<number>`.
**Data Shape:** All hooks return STABLE MotionValue instances (`useConstant` factory); option objects are keyed by `JSON.stringify(options)` in effect deps.

### Decisive source
```ts
// use-follow-value.ts
const { isStatic } = useContext(MotionConfigContext)
if (isStatic) return useTransform(getFromSource)     // early-return AFTER conditional hook count stabilizes
const value = useMotionValue(getFromSource())
useInsertionEffect(() => attachFollow(value, source, options), [value, JSON.stringify(options)])

// use-combine-values.ts
const updateValue = () => value.set(combineValues())
updateValue()                                        // synchronous during render!
useIsomorphicLayoutEffect(() => {
    const scheduleUpdate = () => frame.preRender(updateValue, false, true)
    const subscriptions = values.map((v) => v.on("change", scheduleUpdate))
    return () => { subscriptions.forEach(u => u()); cancelFrame(updateValue) }
})                                                   // no dep array: resubscribe every commit

// use-velocity.ts — keep polling until velocity decays to zero
const updateVelocity = () => { const latest = value.getVelocity(); velocity.set(latest)
    if (latest) frame.update(updateVelocity) }
useMotionValueEvent(value, "change", () => frame.update(updateVelocity, false, true))
```

**Flow:** `useInsertionEffect` attaches the follow passive effect BEFORE layout effects read styles — attachment order guarantees the first paint after a prop change already springs from the correct base. Combined values update SYNCHRONOUSLY during render (so first DOM output is fresh) then keep updating via coalesced preRender frames; the dep-array-less layout effect re-subscribes each commit because the `values`/`combineValues` identities may change while the returned value must not. Static mode (Framer canvas / SSR-ish contexts) swaps animation for direct re-render-on-change. `useVelocity` schedules its update at the END of the current frame (`immediate=true` inside `frame.update`) and self-reschedules while non-zero so the derived velocity value settles to exactly 0 instead of freezing mid-decay.
**Invariant:** Never attach follow effects in `useEffect` — children's layout effects would read stale styles on mount. The `JSON.stringify(options)` dep means callers may pass inline object literals safely; mutating options in place does NOT re-attach. `useMotionValue` uses `useConstant`, not `useState`/`useRef(lazy)`, so no re-render can recreate the value.
**Probe:** `packages/framer-motion/src/value/__tests__/use-spring.test.tsx` (`runSpringTests` :49-223 — standalone + tracked-source modes through real React render). Runner BLOCKED here (no installed workspace deps in inspo clone); deterministic equivalents executed against motion-dom layer (P17/P18 cover attach semantics; P12/P13 cover scheduling). Recorded honestly as runner block with upstream suite cited.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-framer-motion", query: "useSpring useFollowValue useCombineMotionValues useVelocity", limit: 10, fields: ["signature", "name", "file"] });
```
Verified line-exact: `framer-motion.src.value.use-spring.useSpring` :44-49.

## Verdict
Adopt insertion-effect attachment, render-phase initial sync, dep-less resubscription, JSON-keyed option identity, and the velocity decay poller. Adapt `MotionConfigContext.isStatic` to your framework's static-mode signal. Omit the four-overload TS surface (keep one canonical overload). Caveat: react-layer suites exist upstream but were not executable in this environment.
