<!-- capsule-v2 -->
# Solid store proxy traps — how does createStore track fine-grained property reads while blocking direct mutation?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What do the get/has traps register, and which symbol fast paths must a porter preserve?

## store.ts proxyTraps + wrap
**Path/Symbol:** `packages/solid/store/src/store.ts:proxyTraps` (:174-226), `wrap` (:49-84), helpers `getNodes/getNode/trackSelf/ownKeys/proxyDescriptor` (:138-172).
**Signature:** module-level `const proxyTraps: ProxyHandler<StoreNode>`; `wrap<T extends StoreNode>(value: T): T` caches the proxy on the raw node under `$PROXY`.
**Data Shape:** Symbols `$RAW` ("store-raw"), `$NODE`, `$HAS`, `$SELF`; `DataNodes = Record<PropertyKey, DataNode>` where each node is an `{equals:false, internal:true}` signal with a `.$(v?)` setter alias.

### Decisive source
```ts
get(target, property, receiver) {
    if (property === $RAW) return target;
    if (property === $PROXY) return receiver;
    if (property === $TRACK) { trackSelf(target); return receiver; }
    const nodes = getNodes(target, $NODE);
    const tracked = nodes[property];
    let value = tracked ? tracked() : target[property];
    ...
    if (!tracked) {
      const desc = Object.getOwnPropertyDescriptor(target, property);
      if (
        getListener() &&
        (typeof value !== "function" || Object.prototype.hasOwnProperty.call(target, property)) &&
        !(desc && desc.get)
      )
        value = getNode(nodes, property, value)();
    }
    return isWrappable(value) ? wrap(value) : value;
},
has(target, property) {
    ... // $RAW/$PROXY/$TRACK/$NODE/$HAS/__proto__ always true
    getListener() && getNode(getNodes(target, $HAS), property)();
    return property in target;
},
set() { if (IS_DEV) console.warn("Cannot mutate a Store directly"); return true; },
```

**Flow:** property read → serve from the per-property signal if it exists (this REGISTERS dependency) → else read raw and create+track the signal lazily ONLY when a Listener is present → wrap nested wrappables recursively on the way out. `has` tracks membership separately in `$HAS` nodes so `"x" in store` is reactive. `ownKeys`/spread track `$SELF`. Class instances: getters from the prototype are re-bound to the PROXY during `wrap` so `this` sees reactive reads.
**Invariant:** Direct `set/deleteProperty` are silent no-op lies returning `true` (dev-warned) — all writes go through `setStore` (setProperty). Functions are NOT wrapped as signals unless they're OWN properties (`hasOwnProperty` check) — methods stay callable without tracking. The five symbol fast paths ($RAW/$PROXY/$TRACK/$NODE/$HAS) plus `__proto__` must short-circuit BEFORE generic handling or recursion/deep-equality machinery breaks.
**Probe:** `grep -c 'trackSelf(target);' packages/solid/store/src/store.ts` → `2` ($TRACK trap + ownKeys). Behavior pinned by store.spec describe("Tracking State changes") (:250+) and describe("State Getters") (:40).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "proxyTraps getNodes getNode trackSelf", limit: 10 });
```

## Verdict
Adopt trap-for-proxy, signal-per-property lazy nodes verbatim. Adapt symbol names/registration to host. Omit prototype/class getter re-binding until you need class stores.
