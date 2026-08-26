<!-- capsule-v2 -->
# RefImpl + ObjectRefImpl — how do refs wrap values, unwrap on set, and link to reactive properties?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** What must a ref port keep so deep refs auto-reactive their payload, shallow refs don't, and toRef stays write-through to its source?

## RefImpl class + property-linked ObjectRefImpl
**Path/Symbol:** `packages/reactivity/src/ref.ts:RefImpl` (:114-165), `createRef` (:104-109), `triggerRef` (:192-206), `ObjectRefImpl` (:372-425), `GetterRefImpl` (:427-436), `CustomRefImpl` (:293-317), `proxyRefs/shallowUnwrapHandlers` (:253-283), `toRef` dispatch (:500-514).
**Signature:** `class RefImpl<T> { _value: T; _rawValue: T; dep: Dep; get value(): T; set value(v): void }`; `class ObjectRefImpl { get dep(): Dep | undefined }`.
**Data Shape:** RefImpl keeps `_rawValue` (raw or shallow-as-is) AND `_value` (deep: `toReactive(value)`). Setter computes `useDirectValue = isShallow || isShallow(newValue) || isReadonly(newValue)`; only then skips toRaw/toReactive. Change gate: `hasChanged(newValue, _rawValue)`.

### Decisive source
```ts
set value(newValue) {
  const oldValue = this._rawValue
  const useDirectValue = this[ReactiveFlags.IS_SHALLOW] || isShallow(newValue) || isReadonly(newValue)
  newValue = useDirectValue ? newValue : toRaw(newValue)
  if (hasChanged(newValue, oldValue)) {
    this._rawValue = newValue
    this._value = useDirectValue ? newValue : toReactive(newValue)
    this.dep.trigger(/* SET 'value' */)
  }
}
// ObjectRefImpl.get.dep resolves the LIVE property dep from the raw object:
get dep(): Dep | undefined { return getDepFromReactive(this._raw, this._key) }
```

**Flow:** `ref()` returns existing refs untouched (`createRef` isRef check); deep ref wraps payload with reactive ONCE at set-time — reads of `_value` are plain property reads plus `dep.track()`; `shallowRef` stores as-is and requires manual `triggerRef`. `ObjectRefImpl` (toRef(object,'k')) has NO own dep: reads/writes forward through the source proxy so tracking lands on the property's real Dep.
**Invariant:** Comparison happens against `_rawValue`, not `_value` — comparing against the reactive wrapper would always differ and over-trigger; array integer-key refs are NOT unwrapped on read (baseHandlers :120-123 mirrors this), which ObjectRefImpl reproduces via its proxy-layer walk (:388-397). GetterRefImpl (function source) is readonly and never caches beyond `_value` assignment.
**Probe:** `packages/reactivity/__tests__/ref.spec.ts:273` (`toRef`) + `:314-325` (toRef with defaultValue `u.value === 7` before first write).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "RefImpl createRef shallowRef", limit: 10 });
```

## Verdict
Adopt the dual-value (_rawValue/_value) setter contract and dep-less linked refs. Adapt customRef if your host lacks user-facing track/trigger hooks. Omit UnwrapRef type algebra (compile-time concern).
