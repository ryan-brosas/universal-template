<!-- capsule-v2 -->
# Store unwrap contract — what does unwrap() guarantee about its input, its output, and itself under SSR?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (gen 2026-08-25T20:12:15Z). **Question:** Is unwrap a copy, a cast, or a mutation — and what must a porter preserve about each?

## store.ts unwrap recursion + server identity twin
**Path/Symbol:** `packages/solid/store/src/store.ts:unwrap` (:110-136); server twin `packages/solid/store/src/server.ts:unwrap` (:28-30).
**Signature:** `function unwrap<T>(item: any, set = new Set()): T` (client); `function unwrap<T>(item: T): T { return item; }` (server).
**Data Shape:** `set` is a cycle-guard accumulator threaded through recursion; input may be a store proxy, raw object, array, frozen object, or non-wrappable leaf. Fan-in: 12 callers across modifiers (`reconcile`, `produce`, `set`, `get`, `applyState`), mutable, and store (`createStore`, `setStore`, `updatePath`, `updateArray`) — per trace_path inbound.

### Decisive source
```ts
let result, unwrapped, v, prop;
if ((result = item != null && item[$RAW])) return result;   // proxy → raw in O(1)
if (!isWrappable(item) || set.has(item)) return item;       // leaf or already-on-stack

if (Array.isArray(item)) {
  if (Object.isFrozen(item)) item = item.slice(0);          // frozen ⇒ COPY before mutating
  else set.add(item);
  for (let i = 0, l = item.length; i < l; i++) {
    v = item[i];
    if ((unwrapped = unwrap(v, set)) !== v) item[i] = unwrapped;  // IN-PLACE replacement
  }
} else {
  if (Object.isFrozen(item)) item = Object.assign({}, item);
  else set.add(item);
  const keys = Object.keys(item),
    desc = Object.getOwnPropertyDescriptors(item);
  for (let i = 0, l = keys.length; i < l; i++) {
    prop = keys[i];
    if (desc[prop].get) continue;                            // getters are never invoked/replaced
    v = item[prop];
    if ((unwrapped = unwrap(v, set)) !== v) item[prop] = unwrapped;
  }
}
return item;
```

**Flow:** `$RAW` fast path returns the proxy's backing node immediately; leaves and on-stack items pass through untouched; wrappable containers get their nested proxies REPLACED with raw nodes recursively — mutating the container they came from. Frozen containers cannot absorb replacements, so they are shallow-copied first (the only case where unwrap allocates). Getter properties are skipped both as replacement targets and as recursion roots.
**Invariant:** On mutable (non-frozen) input, unwrap is an IN-PLACE normalization, not a copy: after `reconcile(value)` captures `v = unwrap(value)` at options time (:141 of modifiers.ts), later mutations to the caller's object are visible to every subsequent reconcile application — and conversely the store's raw tree now shares those nested nodes. The cycle-guard `Set` makes self-referential stores terminate. Under SSR compile-out the twin is the IDENTITY function, which is sound only because server stores have no proxies to strip (server `isWrappable` also drops the `obj[$PROXY]` check).
**Probe:** `packages/solid/store/test/modifiers.spec.ts:72` `expect(Object.is(unwrap(state.users[0]), JOHN)).toBe(true);` pins that keyed reconcile moves the SAME raw node between indices (identity preservation is observable through unwrap). "Top Level Object Mutation" (:239-250) pins `unwrap(state.data)).toBe(next)` — produce-assigned raw objects come back referentially intact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "unwrap raw node store proxy conversion", limit: 10 });
```

## Verdict
Adopt the three-tier contract: O(1) $RAW exit, in-place nested stripping with cycle guard, copy only when frozen. Adapt the symbol names ($RAW) to your proxy brand. Omit nothing on the client side; on a signal-free server twin the identity function is correct ONLY together with a proxy-free isWrappable.
