<!-- capsule-v2 -->
# createReactiveObject + ReactiveFlags — when does a value become a proxy, and which proxy comes back?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** What admission rules and flag protocol must a porter copy so `reactive/readonly/shallow*` are idempotent and mutually composable?

## Four-quadrant factory with WeakMap memoization
**Path/Symbol:** `packages/reactivity/src/reactive.ts:createReactiveObject` (:262-306), `targetTypeMap` (:43-56), `reactive` (:87-99), `readonly` (:209-219), `isReactive/isReadonly/isProxy/toRaw` (:327-394), `markRaw` (:420-425); `packages/reactivity/src/constants.ts:ReactiveFlags` (:17-24).
**Signature:** `createReactiveObject(target, isReadonly, baseHandlers, collectionHandlers, proxyMap): object`; `toRaw<T>(observed: T): T` (recursive).
**Data Shape:** TargetType enum {INVALID=0, COMMON=1, COLLECTION=2} from `toRawType`: Object|Array→COMMON (baseHandlers), Map|Set|WeakMap|WeakSet→COLLECTION (collectionHandlers), everything else INVALID (returned as-is). One WeakMap per quadrant memoizes raw→proxy.

### Decisive source
```ts
// already a Proxy? return it — EXCEPT readonly(reactive(x)) must wrap:
if (target[ReactiveFlags.RAW] && !(isReadonly && target[ReactiveFlags.IS_REACTIVE])) return target
// opt-outs: markRaw'ed or non-extensible targets pass through untouched
if (target[ReactiveFlags.SKIP] || !Object.isExtensible(target)) return target
const existingProxy = proxyMap.get(target); if (existingProxy) return existingProxy
const targetType = targetTypeMap(toRawType(target))
if (targetType === TargetType.INVALID) return target
const proxy = new Proxy(target, targetType === COLLECTION ? collectionHandlers : baseHandlers)
proxyMap.set(target, proxy)
```

**Flow:** flags are answered by the GET trap reading handler-local booleans (`__v_isReactive ⇒ !isReadonly` etc.) — the RAW object itself stores nothing, so `isReactive(readonly(reactive(x)))` walks `.raw` recursively in isReactive (:327-332). Flag keys live on Dep/EffectScope instances too (`__v_skip`) so internal objects never get proxied.
**Invariant:** Idempotency is per-quadrant: re-reactive returns the SAME proxy (memo), but readonly-over-reactive intentionally creates a SECOND wrapper; frozen/sealed targets are silently non-reactive (non-extensible check) — porters who skip that check throw TypeError from the Proxy constructor.
**Probe:** `packages/reactivity/__tests__/reactive.spec.ts:191` (same-proxy identity) + `readonly.spec.ts:229` (#1772 composability).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "createReactiveObject targetTypeMap proxyMap", limit: 10 });
```

## Verdict
Adopt the admission ladder order exactly (proxy-check → skip/extensible → memo → type gate → handler split). Adapt INVALID-type policy only with care: allowing Date/RegExp proxies breaks identity-sensitive built-ins. Omit ShallowReactiveBrand type machinery (TS-only).
