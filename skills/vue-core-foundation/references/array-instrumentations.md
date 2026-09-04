<!-- capsule-v2 -->
# Array instrumentations — how do array methods get ARRAY_ITERATE tracking, raw-search fallback, and loop-safe mutations?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** Which array methods must a porter intercept, and with what tracking/wrapping contracts, to keep reactive arrays correct?

## Three instrumentation families over the proxy
**Path/Symbol:** `packages/reactivity/src/arrayInstrumentations.ts:arrayInstrumentations` (:42-230), `reactiveReadArray` (:20-25), `iterator` (:233-261), `apply` (:270-306), `reduce` (:309-337), `searchProxy` (:340-357), `noTracking` (:361-372).
**Signature:** `reactiveReadArray<T>(array: T[]): T[]`, `shallowReadArray<T>(arr: T[]): T[]`, `noTracking(self, method, args?)`.
**Data Shape:** Identity table (`__proto__: null`) keyed by method name; installed from `BaseReactiveHandler.get` BEFORE Reflect for non-readonly targets. Families: (1) whole-array readers taking one ARRAY_ITERATE dep; (2) identity searches with raw retry; (3) length mutators running untracked.

### Decisive source
```ts
// identity-sensitive search: try as-given, retry with raw on miss
function searchProxy(self, method, args) {
  const arr = toRaw(self)
  track(arr, TrackOpTypes.ITERATE, ARRAY_ITERATE_KEY)
  const res = arr[method](...args)                       // may hold proxies
  if ((res === -1 || res === false) && isProxy(args[0])) { args[0] = toRaw(args[0]); return arr[method](...args) }
  return res
}
// length-altering mutators: pause tracking + batch or effects see their own write (#2137)
function noTracking(self, method, args = []) {
  pauseTracking(); startBatch()
  const res = (toRaw(self))[method].apply(self, args)
  endBatch(); resetTracking()
  return res
}
```

**Flow:** readers (`forEach/map/every/some/filter/find*/concat/join/toReversed/toSorted/toSpliced/entries/values/[Symbol.iterator]`) call `shallowReadArray` → single `track(raw, ITERATE, ARRAY_ITERATE)` → callbacks receive WRAPPED items via `toWrapped` (readonly(reactive(x)) yields readonly-of-reactive) and the PROXY as third arg — except user-subclassed methods detected by `methodFn !== arrayProto[method]`, which are invoked untouched (#11759); `reduce` additionally wraps a missing initial accumulator once.
**Invariant:** The iterator simplification is deliberate: creating `.next()` iterator takes ONE ARRAY_ITERATE dep at creation time even though lazily it would read per-index (in-source comment :238-245) — porters "fixing" this to lazy tracking change invalidation granularity. `push/pop/shift/unshift/splice` MUST run inside pause+batch or an effect reading length loops forever.
**Probe:** `packages/reactivity/__tests__/reactiveArray.spec.ts:201` (`shift on Array should trigger dependency once`) + `:479` (`find and co.`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "arrayInstrumentations noTracking searchProxy", limit: 10 });
```

## Verdict
Adopt the three families and the subclass escape hatch. Adapt wrapping choice (toReactive vs toShallow) to your quadrant. Omit flat/flatMap instrumentation (upstream explicitly skipped: comment :125).
