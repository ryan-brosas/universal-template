<!-- capsule-v2 -->
# Proxy get/set handlers — how do reads track, writes trigger, and identity checks avoid false triggers?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** Which trap details must a ported proxy layer reproduce so tracking keys, ref unwrapping, and ADD-vs-SET semantics are exact?

## BaseReactiveHandler + MutableReactiveHandler
**Path/Symbol:** `packages/reactivity/src/baseHandlers.ts:BaseReactiveHandler.get` (:55-134), `MutableReactiveHandler.set` (:142-192), `deleteProperty` (:194-205), `has` (:207-213), `ownKeys` (:215-222), `hasOwnProperty` shim (:41-47), `ReadonlyReactiveHandler` (:225-249).
**Signature:** `get(target, key, receiver): any`, `set(target, key, value, receiver): boolean`, `deleteProperty(target, key): boolean`.
**Data Shape:** Four singleton handler sets (mutable/readonly × deep/shallow) shared by all proxies; per-target proxy memoization lives in reactiveMap/readonlyMap/shallowReactiveMap/shallowReadonlyMap.

### Decisive source
```ts
// set: hadKey decides ADD vs SET; prototype-chain shadowing must not trigger
const hadKey = isArrayWithIntegerKey ? Number(key) < target.length : hasOwn(target, key)
const result = Reflect.set(target, key, value, isRef(target) ? target : receiver)
if (target === toRaw(receiver) && result) {
  if (!hadKey) trigger(target, TriggerOpTypes.ADD, key, value)
  else if (hasChanged(value, oldValue)) trigger(target, TriggerOpTypes.SET, key, value, oldValue)
}
// get: RAW fast-path must accept user proxies of the reactive proxy
if (key === ReactiveFlags.RAW) {
  if (receiver === proxyMap.get(target) || Object.getPrototypeOf(target) === Object.getPrototypeOf(receiver)) return target
  return   // early undefined otherwise
}
```

**Flow:** get → flag keys (`__v_isReactive/__v_isReadonly/__v_isShallow/__v_raw`) answered WITHOUT Reflect → non-trackable keys (`__proto__`, built-in Symbols) pass through → array instrumentations intercept before Reflect → `track(target, GET, key)` only when NOT readonly → shallow returns raw result → nested refs unwrap EXCEPT array+integer-key → nested objects lazily wrapped via `reactive(res)`/`readonly(res)` on the way OUT.
**Invariant:** Writes to inherited properties (`target !== toRaw(receiver)` after a successful set) must NOT trigger — that is the prototype-shadowing guard; `hadKey` for arrays uses index-vs-length, not hasOwn; setting an identical primitive value must skip SET entirely. The `hasOwnProperty` trap shim String()-coerces non-symbol keys (#10455).
**Probe:** `packages/reactivity/__tests__/reactive.spec.ts:191` (`observing the same value multiple times should return same Proxy`) + `reactiveArray.spec.ts:234` (`add existing index on Array should not trigger length dependency`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "BaseReactiveHandler get set", limit: 10 });
```

## Verdict
Adopt trap ordering (flags → instrumentations → track → lazy wrap) and the receiver-identity guards verbatim. Adapt the four-map WeakMap scheme if your host proxies fewer variants. Omit readonly DEV warnings in prod builds.
