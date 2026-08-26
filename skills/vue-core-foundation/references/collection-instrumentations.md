<!-- capsule-v2 -->
# Collection instrumentation — how do Map/Set/Weak* become reactive when Proxy cannot intercept their methods?

**Source:** vue-core MIT `main@e2bede96`; Codebase Memory project `ext-vue-core`. **Question:** How does a porter make collections trackable and triggerable without instrumenting the raw objects' prototype?

## Instrumentation-getter redirect on get-only handlers
**Path/Symbol:** `packages/reactivity/src/collectionHandlers.ts:createInstrumentations` (:96-268), `createIterableMethod` (:33-75), `createInstrumentationGetter` (:270-294), mutable add/set/delete/clear (:168-253), `checkIdentityKeys` (:313-329).
**Signature:** `createInstrumentationGetter(isReadonly: boolean, shallow: boolean): ProxyHandler['get']`; handler objects carry ONLY a `get` trap.
**Data Shape:** Per (readonly, shallow) quadrant, one frozen instrumentations object maps `get/size/has/forEach/add/set/delete/clear/keys/values/entries/[Symbol.iterator]` to wrappers; the proxy's single get-trap redirects to instrumentations only when the key exists there AND on the target.

### Decisive source
```ts
// map.get must track BOTH raw and reactive keys, then fall through to #3602:
get(this: MapTypes, key) {
  const target = this[ReactiveFlags.RAW], rawTarget = toRaw(target), rawKey = toRaw(key)
  if (!readonly) { if (hasChanged(key, rawKey)) track(rawTarget, GET, key); track(rawTarget, GET, rawKey) }
  const { has } = getProto(rawTarget)
  const wrap = shallow ? toShallow : readonly ? toReadonly : toReactive
  if (has.call(rawTarget, key)) return wrap(target.get(key))
  else if (has.call(rawTarget, rawKey)) return wrap(target.get(rawKey))
  else if (target !== rawTarget) target.get(key)  // #3602 readonly(reactive(map)): let inner reactive map track itself
}
```

**Flow:** any property read on a collection proxy → instrumentation-getter → flag keys answered directly (`__v_raw` returns TARGET — note for collections the target IS already the proxy's input, not a second unwrap) → method reads dispatch to instrumentations which operate via raw-target prototypes and wrap values on the way out (`toReactive/toReadonly/toShallow`) → mutations forward to the raw object FIRST ("forward before queueing reactions"), compute hadKey/hadItems BEFORE the op, then trigger ADD/SET/DELETE/CLEAR.
**Invariant:** `size`, `forEach`, and iterators always track ITERATE_KEY; map-only `keys()` tracks MAP_KEY_ITERATE_KEY instead so key-only loops don't re-run on value changes; adding a raw-vs-reactive duplicate of an existing key warns in DEV (`checkIdentityKeys`) because identity ambiguity breaks lookups.
**Probe:** `packages/reactivity/__tests__/readonly.spec.ts:229` (#1772 `readonly + reactive should make get() value also readonly + reactive`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-vue-core", query: "instrumentations createIterableMethod", limit: 10 });
```

## Verdict
Adopt the get-redirect + raw-proto-forwarding pattern wholesale. Adapt wrap choice per your deep/shallow matrix. Omit WeakMap/WeakSet iteration methods (impossible by spec) — upstream simply never registers them for weak collections.
