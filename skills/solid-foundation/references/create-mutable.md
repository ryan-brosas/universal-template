<!-- capsule-v2 -->
# Solid createMutable — how does the writable twin differ from createStore's proxy, and what does it add for methods and setters?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What exactly changes between store.ts and mutable.ts proxy machinery?

## mutable.ts: writable traps + batched array-method wrappers
**Path/Symbol:** `packages/solid/store/src/mutable.ts` (whole file :1-157): local `proxyDescriptor` (:17-35), `proxyTraps` (:37-94), `wrap` (:96-141), `createMutable` (:143-153), `modifyMutable` (:155-157).
**Signature:** `createMutable<T extends StoreNode>(state: T, options?): T` — returns a PROXY you mutate directly; `modifyMutable(state, modifier)` batches `modifier(unwrap(state))`.
**Data Shape:** Same $RAW/$NODE/$HAS/$PROXY symbol protocol as store.ts. Key deltas vs read-only traps: real `set`/`deleteProperty` (`batch(() => setProperty(target, property, unwrap(value)))`), and an Array.prototype method wrapper branch in `get`.

### Decisive source
```ts
else if (value != null && isFunction && value === Array.prototype[property as any]) {
    return (...args: unknown[]) =>
      batch(() => Array.prototype[property as any].apply(receiver, args));
}
...
set(target, property, value) {
    batch(() => setProperty(target, property, unwrap(value)));
    return true;
},
```

**Flow:** identical lazy per-property signals on read; but inherited array methods (push/splice/pop…) are intercepted and re-invoked against the RECEIVER inside ONE batch — so `store.list.push(x)` fires one update, not two (index + length). Writes unwrap the assigned value first (no proxies stored raw-side) then go through the same ordered setProperty fan-out. Class support is deeper than store.ts: wrap walks the WHOLE prototype chain (`while (curProto != null)`) re-binding getters AND setters; setter calls are wrapped in batch.
**Invariant:** Mutable stores break referential transparency guarantees of createStore — passing them across boundaries lets anyone mutate; that's why Solid docs recommend them for leaf/local state only. The `value === Array.prototype[property]` identity check means only BUILT-IN array methods get batch-wrapped — custom functions are returned as-is.
**Probe:** `grep -c 'batch(() => setProperty(target, property, unwrap(value)));' packages/solid/store/src/mutable.ts` → `1`. Behavior pinned by store/test/mutable.spec.ts describes "Simple update modes" (:77), "Tracking State changes" (:137), "Handling functions in state" (:204), "In Operator" (:287).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "createMutable modifyMutable setterTraps batch", limit: 10 });
```

## Verdict
Adopt as the ergonomics layer when host code prefers direct mutation; keep createStore for shared state. Adapt method-batching to your array wrappers. Omit prototype-chain setter rebinding if you don't host class instances.
