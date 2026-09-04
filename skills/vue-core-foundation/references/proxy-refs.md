<!-- capsule-v2 -->
# proxyRefs shallow unwrap — how does setup-return get ref-unwrapping without deep proxies?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** What minimal proxy semantics make `obj.count` read/write a nested ref transparently, and when must the proxy be skipped?

## shallowUnwrapHandlers with write-through-to-ref
**Path/Symbol:** `packages/reactivity/src/ref.ts:shallowUnwrapHandlers` (:253-267), `proxyRefs` (:277-283), `unref/toValue` (:229-251).
**Signature:** `proxyRefs<T extends object>(objectWithRefs: T): ShallowUnwrapRef<T>`; handlers implement only get/set.
**Data Shape:** get: `key === __v_raw ? target : unref(Reflect.get(...))`; set: if old value isRef and new is not → assign to `.value` of the OLD ref (identity preserved); else plain Reflect.set.

### Decisive source
```ts
const shallowUnwrapHandlers: ProxyHandler<any> = {
  get: (target, key, receiver) =>
    key === ReactiveFlags.RAW ? target : unref(Reflect.get(target, key, receiver)),
  set: (target, key, value, receiver) => {
    const oldValue = target[key]
    if (isRef(oldValue) && !isRef(value)) { oldValue.value = value; return true }
    else return Reflect.set(target, key, value, receiver)
  },
}
export function proxyRefs(objectWithRefs) {
  return isReactive(objectWithRefs) ? objectWithRefs : new Proxy(objectWithRefs, shallowUnwrapHandlers)
}
```

**Flow:** template/render access → proxy get unwraps one level (`unref`), so `props.count` reads `.value`; assignment replaces the ref's CONTENT while keeping the same ref object alive — subscriptions survive; assigning a NEW ref overwrites the property wholesale.
**Invariant:** The `isReactive` short-circuit matters: reactive objects already unwrap refs on GET via baseHandlers (:120-123), double-proxying would break RAW identity and add overhead. Unwrapping is exactly ONE level deep — nested refs inside objects stay refs.
**Probe:** `packages/runtime-core/__tests__/hmr.spec.ts:898` (`multi reload child wrapped in Suspense + KeepAlive` — setup returns `{ count: ref(0) }`, template `{{ count }}` renders `<div>0</div>` then 1/2 after reloads: proxyRefs unwrap pinned end-to-end) + `componentPublicInstance.spec.ts:39` (`setupState` write-through).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "proxyRefs shallowUnwrapHandlers ObjectRefImpl", limit: 10 });
```

## Verdict
Adopt the two-trap handler verbatim; it is 15 lines and load-bearing for every Vue-like render layer. Adapt the isReactive skip if your host has no deep-reactive equivalent. Omit ShallowUnwrapRef type mapping.
