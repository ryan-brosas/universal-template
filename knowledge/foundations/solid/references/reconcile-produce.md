<!-- capsule-v2 -->
# Solid reconcile & produce — how does keyed diffing mutate a store in place, and how does produce wrap it in immer-style traps?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What does applyState reuse vs replace, and where is the key option load-bearing?

## modifiers.ts: applyState recursion + setterTraps
**Path/Symbol:** `packages/solid/store/src/modifiers.ts:applyState` (:15-133), `reconcile` (:136-147), `produce` (:181-195) + `setterTraps` (:150-178).
**Signature:** `reconcile<T, U>(value: T, options?: { key?: string | null; merge?: boolean }): (state: U) => T`; `produce<T>(fn: (state: T) => void): (state: U) => U`.
**Data Shape:** `$ROOT` sentinel property for the top call; `producers: WeakMap` caches one setter-proxy per raw node so repeated `produce(fn)` calls on the same subtree reuse proxies; default `key = "id"`.

### Decisive source
```ts
if (
    property !== $ROOT &&
    (!isWrappable(target) ||
      !isWrappable(previous) ||
      isArray !== Array.isArray(previous) ||
      (key && target[key] !== previous[key]))   // KEY MISMATCH ⇒ replace whole subtree
  ) {
    setProperty(parent, property, target);
    return;
}
```

**Flow:** reconcile returns a mutator for setStore: walk target vs previous — identical references short-circuit; non-wrappable/type-flip/key-mismatch nodes are REPLACED via setProperty (which fires the minimal signal set); arrays take the SAME prefix/suffix/backwards-map diff as mapArray (with key-valued identity when `key` set, else value identity); plain objects recurse per-key and then DELETE previous keys that are undefined in target. `produce` hands `fn` a recursive proxy whose `set/deleteProperty` route through `setProperty(unwrap(value))`, batching each.
**Invariant:** With `key: "id"` array items are matched by id — reordering moves nodes instead of overwriting, preserving nested state and DOM. `merge: true` forces deep-merge even for keyed arrays. The WeakMap producer cache is required for correctness of nested produces, not just speed.
**Probe:** `grep -c 'keyVal = key && item ? item[key] : item;' packages/solid/store/src/modifiers.ts` → `2`; `grep -c 'const { merge, key = "id" } = options,' packages/solid/store/src/modifiers.ts` → `1`. Behavior pinned by store/test/modifiers.spec.ts describes "setState with reconcile" (:13), "setState with produce" (:179), "modifyMutable with reconcile" (:314).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "applyState reconcile produce setterTraps", limit: 10 });
```

## Verdict
Adopt applyState's replace-triggers + keyed array diff verbatim as the canonical fine-grained merge. Adapt produce's proxy to your write API. Omit `merge` mode if you never need unkeyed merges.
