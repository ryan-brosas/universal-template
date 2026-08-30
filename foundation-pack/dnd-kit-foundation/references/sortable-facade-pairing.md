<!-- capsule-v2 -->
# Sortable facade — draggable+droppable pairing, split disabled, and WeakStore drag snapshots

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How does one Sortable keep two registry identities in sync, and where do initialIndex/initialGroup live during a drag?

## Sortable class
**Path/Symbol:** `packages/dom/src/sortable/sortable.ts:148-578` (+ `utilities.ts` isSortable/isSortableOperation).
**Signature:** `new Sortable({id, index, group?, disabled?: boolean|{draggable,droppable}, transition?, plugins? = [SortableKeyboardPlugin, OptimisticSortingPlugin], target?, ...}, manager?)`; composes `SortableDroppable` + `SortableDraggable` (subclasses exposing index/group/initialIndex/initialGroup).
**Data Shape:** module-level `WeakStore<DragDropManager, id, {initialIndex, initialGroup}>` — per-manager, per-id TemporaryState written by an effect when `status.dragging` begins and CLEARED on the next `initializing`.

### Decisive source
```ts
// effect #1 — snapshot at drag start
() => {
  const status = this.manager?.dragOperation.status;
  if (status?.initializing && this.id === this.manager?.dragOperation.source?.id) {
    store.clear(this.manager);            // fresh op → wipe previous snapshot
  }
  if (status?.dragging) {
    store.set(this.manager, this.id,
      untracked(() => ({initialIndex: this.index, initialGroup: this.group})));
  }
},

// element setter — batched dual-identity sync with change guards
set element(element) {
  batch(() => {
    if (!droppableElement || droppableElement === previousElement)
      this.droppable.element = element;
    if (!draggableElement || draggableElement === previousElement)
      this.draggable.element = element;
    this.#element = element;
  });
}

// move-feedback coupling: 'move' feedback disables dropping while detached
if (feedback === 'move' && isDragSource) this.droppable.disabled = !target;
```

**Flow:** constructor builds droppable FIRST then draggable (both share input) → three kernel effects handle snapshotting, index-change animation, and move-feedback gating → setters (`id`, `element`, `type`, `data`, `disabled`) fan out to both halves inside `batch()` so observers never see half-updated pairs; register/unregister/destroy likewise pair up. The `disabled` getter collapses symmetric values back to boolean (`draggable === droppable ? draggable : {draggable, droppable}`), pinned across ~20 test cases.
**Invariant:** initial* values must be captured UNTRACKED exactly once per operation and survive until the NEXT initializing phase (OptimisticSorting rollback reads them after cancel); the droppable's `target` slot lets list rows use a different drop surface than the dragged element without breaking the shared identity.
**Probe:** `packages/dom/tests/sortable-utilities.test.ts:156-265` (boolean/object disabled matrix both directions + reset); isSortable narrowing :56-150.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "Sortable", name_pattern: "^Sortable$", limit: 10 });
```

## Verdict
Adopt the two-entity pairing with batched fan-out setters and manager-scoped initial snapshots; adapt default plugins/transition to your UX; omit the target/source element split for simple lists.
