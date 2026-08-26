<!-- capsule-v2 -->
# Optimistic sorting reconciliation — DOM-first reordering with snapshot-based aborts and cancel rollback

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How can the UI reorder instantly on dragover while still converging with app state, and how does a canceled drag undo itself?

## OptimisticSortingPlugin
**Path/Symbol:** `packages/dom/src/sortable/plugins/OptimisticSortingPlugin.ts:16-231` (+ helpers `getSortableIndices`/`hasChanged`).
**Signature:** listens to `dragover` + `dragend` on the manager monitor; group key defaults to `'__default__'`; reorder primitive `targetElement.insertAdjacentElement(targetIndex < sourceIndex ? 'afterend' : 'beforebegin', sourceElement)`.
**Data Shape:** per-group `Map<group|undefined, Set<Sortable>>` rebuilt by scanning registered SortableDroppables; snapshot = `{id → {index, group}}` taken BEFORE the renderer tick.

### Decisive source
```ts
manager.monitor.addEventListener('dragover', (event, manager) => {
  ...
  const sortableIndices = getSortableInstances(); // snapshot BEFORE await
  queueMicrotask(() => {
    if (event.defaultPrevented) return;
    manager.renderer.rendering.then(() => {
      const newInstances = getSortableInstances();
      if (hasChanged(sortableIndices, instances, newInstances)) {
        return;   // app mutated indices meanwhile → ABORT optimistic write
      }
      ...
      const newState = move(state, event);
      if (state === newState) return;             // move vetoed / no-op
      manager.collisionObserver.disable();
      reorder(sourceElement, sourceIndex, targetElement, targetIndex);  // DOM FIRST
      batch(() => { /* then reactive index/group writes */ });
      manager.actions.setDropTarget(source.id)
        .then(() => manager.collisionObserver.enable());  // target = SOURCE
    });
  });
});

// dragend canceled path: restore initialIndex/initialGroup for EVERY sortable,
// after the same hasChanged abort check, using sortByInitialIndex to find the slot.
```

**Flow:** dragover → snapshot indices → wait microtask (veto check) + renderer tick → re-scan; if anything changed under us, bail (app state wins) → compute `move()` over a synthetic grouped state → disable collisions → physically move the DOM node → publish index (and cross-group membership) writes in one batch → retarget collision detection at the source id so subsequent dragovers compare against the moved item. A CANCELED dragend walks every instance back to its initial index/group and reorders the DOM to match — optimistic UI is fully reversible.
**Invariant:** the DOM mutation precedes the reactive writes (so effects measuring layout see the new order); every async continuation must re-validate against its pre-await snapshot (`hasChanged` compares actual `index` values — position-in-set broke gapped-index lists, fixed by regression test :45-55); `move` returning the SAME reference means "no change" and must not trigger writes.
**Probe:** `packages/dom/tests/optimistic-sorting-plugin.test.ts:34-90` (hasChanged matrix incl. gaps + missing member); live probe of both branches executed via lifted module import.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "OptimisticSortingPlugin", name_pattern: "^OptimisticSortingPlugin$", limit: 10 });
```

## Verdict
Adopt snapshot-abort + DOM-first-then-state ordering + canceled-endpoint rollback; adapt `move`'s synthetic state shape to your store; omit collision disabling only if your target resolution cannot oscillate.
