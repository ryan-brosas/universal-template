<!-- capsule-v2 -->
# move / swap helpers — dual-lookup array mutation with optimistic reconciliation

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** Given either a flat array or grouped record, how does the reducer decide WHERE the source goes when ids may be computed and sorting may already have moved it?

## mutate() kernel
**Path/Symbol:** `packages/helpers/src/move.ts:82-342` (`mutate` shared by `move`=arrayMove and `swap`=arraySwap; primitives :12-46).
**Signature:** `move(items, event)` / `swap(items, event)` over `UniqueIdentifier[] | {id}[] | Record<group, Items>`; event carries `{operation: {source, target, canceled}}` + optional preventDefault.
**Data Shape:** pure — returns NEW arrays/records or the SAME reference when nothing changed; `preventDefault()` on the event signals "no change" to optimistic listeners.

### Decisive source
```ts
if (Array.isArray(items)) {
  const sourceIndex = items.findIndex((item) => findIndex(item, source.id));
  const targetIndex = items.findIndex((item) => findIndex(item, target.id));

  if (sourceIndex === -1 || targetIndex === -1) {
    // Fallback: computed IDs that don't match data items → use sortable indices
    if (hasSortableIndices(source)) {
      const from = source.initialIndex, to = source.index;
      if (from === to || from < 0 || from >= items.length) {
        event.preventDefault?.(); return items;    // loud no-op
      }
      return mutation(items, from, to);
    }
    return items;
  }

  // Reconcile optimistic updates
  if (!canceled && 'index' in source && typeof source.index === 'number') {
    const projectedSourceIndex = source.index;
    if (projectedSourceIndex !== sourceIndex) {
      return mutation(items, sourceIndex, projectedSourceIndex);  // trust the sortable
    }
  }
  return mutation(items, sourceIndex, targetIndex);
}
// Grouped case adds: String(id) record keys (numbers!), cross-group splice transfer,
// below-center insertion modifier `isBelowTarget ? 1 : 0`, and the same reconcile ladder.
```

**Flow:** locate source+target by id (item === id OR item.id === id, null-guarded) → if lookup fails AND the draggable duck-types `initialIndex/index`, fall back to those indices with bounds checks → if found but the sortable's projected index differs from its id-found slot, RECONCILE using the projection (this is what makes post-optimistic dragend converge) → else plain move/swap. Canceled operations or missing endpoints = same-reference return + preventDefault.
**Invariant:** never mutates inputs (`arrayMove` slices first); `from === to` returns the original reference so callers can detect no-op; grouped-record keys must go through `getRecordKey` (`String(id)` + hasOwnProperty) because JS object keys are strings even for numeric group ids; the null-item guard in `findIndex` exists because arrays may contain nulls mid-render.
**Probe:** `packages/helpers/tests/move.test.ts` (901L: flat ID-based, optimistic reconcile :171-211, computed-ID fallback :217-289, grouped reconcile incl. numeric groups :361-466, swap twins) — full suite executed GREEN upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "arrayMove mutate", name_pattern: "^move$", limit: 10 });
```

## Verdict
Adopt the three-tier lookup order (id → sortable-index fallback → projection reconcile) verbatim; adapt `hasSortableIndices` duck-typing to your model classes; omit grouped-record support only for strictly flat lists.
