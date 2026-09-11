<!-- capsule-v2 -->
# Solid store writes — how does setProperty fan out node/$HAS/$SELF signals, and how does updatePath route nested/array/filtered paths?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** What is the write-side notification order, and what path grammar does setStore accept?

## setProperty + updatePath + updateArray
**Path/Symbol:** `packages/solid/store/src/store.ts:setProperty` (:228-261), `updateArray` (:276-292), `updatePath` (:294-343), `createStore` (:533-555).
**Signature:** `setProperty(state, property, value, deleting = false)`; `updatePath(current: StoreNode, path: any[], traversed: PropertyKey[] = [])`; `setStore(...args)` wraps everything in `batch`.
**Data Shape:** `path` parts can be: key | key-array (multi-target) | filter fn `(item, i) => bool` | `{from,to,by}` range object — only on arrays. Final arg may be a value or updater `(prev, traversed) => next`.

### Decisive source
```ts
let nodes = getNodes(state, $NODE),
    node: DataNode | undefined;
if ((node = getNode(nodes, property, prev))) node.$(() => value);

if (Array.isArray(state) && state.length !== len) {
    for (let i = state.length; i < len; i++) (node = nodes[i]) && node.$();
    (node = getNode(nodes, "length", len)) && node.$(state.length);
}
(node = nodes[$SELF]) && node.$();
```

**Flow:** equality gate (`state[property] === value` skips; undefined-means-delete) → dev hook → delete-or-assign raw → fire `$HAS` node on presence TRANSITION only (undefined↔defined) → fire the property's `$NODE` signal → if an array shrank, fire every truncated index's signal plus `length` → fire `$SELF` last so whole-object observers/spreads update after fine-grained ones.
**Invariant:** The notification ORDER matters: property nodes before $SELF, and length/truncation signals before $SELF. updatePath refuses traversal through unsafe keys (`__proto__` anywhere as string part; constructor/prototype when INTERIOR), but ALLOWS them as final keys — pinned by store.spec "Prototype pollution guard" (:907+): `setStore("__proto__", "polluted_a", true)` must not touch Object.prototype while `setStore("constructor", "value")` must work. Merge-vs-replace at leaf: wrappable-prev ∧ wrappable-next ∧ non-array ⇒ mergeStoreNode (shallow per-key recursion), else replace.
**Probe:** `grep -c 'node.$(() => value);' packages/solid/store/src/store.ts` → `1`. Behavior pinned by "Prototype pollution guard" describe (:907-960) and "Array setState modes" (:149+).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "setProperty updatePath updatePath traversed", limit: 10 });
```

## Verdict
Adopt the ordered fan-out and path grammar wholesale. Adapt the batch wrapper to host batching. Omit `merge` semantics only if your stores are always replaced wholesale.
