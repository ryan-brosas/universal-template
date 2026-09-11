<!-- capsule-v2 -->
# Collection document-order map — how do portaled React items register in true DOM order without a layout thrash?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** How does the item registry stay sorted by document position when items mount/unmount/reorder across portals?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/collection/src/collection.tsx:createCollection` (:30-261), ItemSlot effect (:195-221), `sortByDocumentPosition` (:284-293), `shallowEqual` latch (:189-193, :266-278).
**Signature:** `createCollection<ItemElement, ItemData>(name) → [{Provider, Slot, ItemSlot}, {createCollectionScope, useCollection, useInitCollection}]`; `useCollection(scope) → OrderedDict<ItemElement, ItemData & {element}>`.
**Data Shape:** `OrderedDict` keyed BY ELEMENT (not id — duplicate ids impossible, identity is the node); every mutation returns either `.toSorted(...)` or `new OrderedDict(map)`; consumer reads the map directly (no subscription callback — readers re-render via context state).

### Decisive source
```ts
setItemMap((map) => {
  if (!element) return map;
  if (!map.has(element)) {
    map.set(element, { ...itemData, element });
    return map.toSorted(sortByDocumentPosition);   // insert ⇒ sort
  }
  return map
    .set(element, { ...itemData, element })
    .toSorted(sortByDocumentPosition);             // data update ⇒ re-sort
});
return () => {
  setItemMap((map) => {
    if (!element || !map.has(element)) return map;
    map.delete(element);
    return new OrderedDict(map);                   // delete ⇒ FRESH identity
  });
};
...
function isElementPreceding(a: Element, b: Element) {
  return !!(b.compareDocumentPosition(a) & Node.DOCUMENT_POSITION_PRECEDING);
}
```

**Flow:** ItemSlot mounts → composed ref captures element → effect registers `{...itemData, element}` and sorts whole map by compareDocumentPosition (portals sort correctly because sorting uses LIVE DOM position, not render order) → unmount deletes and wraps in a NEW OrderedDict so context consumers see changed identity → per-render itemData latched behind shallowEqual in a ref so unstable prop objects don't reschedule effects.
**Invariant:** sort key is DOM position at MUTATION time — a porter who sorts by array insertion order breaks the moment items portal or conditionally reorder; deletion must produce fresh map identity (mutating in place leaves consumers reading stale context); MutationObserver-driven reorder-resort exists but is deliberately commented out (dead code kept as intent marker — do not "restore" it without a consumer that needs mid-session reorder).
**Probe:** byte-exact anchors: `bash -c "cd $REFERENCE_ROOT/external/ui-radix-ui && grep -nF 'Node.DOCUMENT_POSITION_PRECEDING' packages/react/collection/src/collection.tsx"` (:281) and `grep -nF 'new OrderedDict(map)' packages/react/collection/src/collection.tsx"` (:218). Consumer behavior pinned indirectly by select.test.tsx collection-dependent suites (form-reset :272-390 needs correct option gathering).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "OrderedDict itemMap collection document position", limit: 10 });
```

## Verdict
Adopt element-keyed sorted-map + fresh-identity-on-delete; adapt the OrderedDict for a plain Map+sort if you don't need insertion-order semantics elsewhere; omit the legacy `collection-legacy.tsx` entirely (deprecated API). Coverage caveat: no isolated unit spec drives this file at this pin — verified against whole-file read plus consumer-side select tests.
