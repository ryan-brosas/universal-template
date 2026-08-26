<!-- capsule-v2 -->
# Stable collection index — how do list items keep SSR-stable order indexes across hydration and reorders?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** How does useStableCollectionIndex allocate insertion indexes with render-side effects and effect-side release?

## StableCollection / createCollection / useStableCollectionIndex
**Path/Symbol:** `packages/@headlessui-react/src/utils/stable-collection.tsx:3-59`.
**Signature:** `StableCollection({ children })` (context provider owning a ref'd collection); `useStableCollectionIndex(group: string): number`.
**Data Shape:** `groups: Map<group, Map<key, renders>>`; get returns `[index, release]` where index = position of key in insertion-ordered key array.

### Decisive source
```ts
get(group, key) {
  let list = this.groups.get(group) ?? (this.groups.set(group, new Map()), list)
  let renders = list.get(key) ?? 0
  // FIXME (in source): side effect DURING render; release only runs in an effect cleanup,
  // so multiple pre-commit renders can leak counts when a sibling suspends.
  list.set(key, renders + 1)
  let index = Array.from(list.keys()).indexOf(key)
  function release() {
    let renders = list.get(key)
    if (renders > 1) list.set(key, renders - 1)
    else list.delete(key)
  }
  return [index, release]
}
export function useStableCollectionIndex(group) {
  let collection = useContext(StableCollectionContext)   // throws without provider
  if (!collection) throw new Error('You must wrap your component in a <StableCollection>')
  let key = React.useId()
  let [idx, cleanupIdx] = collection.current.get(group, key)
  React.useEffect(() => cleanupIdx, [])
  return idx
}
```

**Flow:** each item calls useStableCollectionIndex during render → its useId key is inserted (or counted up) → index = ordinal of the key among LIVE keys → on unmount the effect-cleanup releases; count>1 decrements, count==1 deletes. Because keys are useId-based they survive SSR→client hydration even if the child ARRAY order differs.
**Invariant:** indexes are dense ordinals over CURRENT members (deleting the first shifts everyone — consumers recompute); the render-phase mutation is a documented, accepted FIXME (sibling-suspend leak), not a bug to "fix" by moving to effects (indexes must exist during render for aria-posinset-style attributes).
**Probe:** deterministic check executed: double-get single-release keeps entry; second release deletes. Direct usage pinned via menu/listbox tab-index stabilization suites (component-level).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "StableCollectionContext", name_pattern: "^useStableCollectionIndex$|^createCollection$", limit: 5 });
```

## Verdict
Adopt the refcount+ordinal scheme when you need stable per-item indexes for aria-setsize/posinset under concurrent rendering; adapt group semantics freely; keep the FIXME caveat in mind — don't adopt if your framework forbids render-phase writes (React StrictMode double-render included).
