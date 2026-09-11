<!-- capsule-v2 -->
# Manager kernel — how do I compose the drag system without breaking modifier lifecycle?

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** Which collaborators must a DragDropManager construct, in what order, and why do per-source modifiers replace (not append to) manager modifiers?

## Manager composition root
**Path/Symbol:** `packages/abstract/src/core/manager/manager.ts:59-197` (`DragDropManager` constructor + destroy).
**Signature:** `new DragDropManager(config?: { plugins?, sensors?, modifiers?, renderer? })` where each array is `Customizable<T> = T | ((defaults: T) => T)` resolved by `resolveCustomizable` (:35-44).
**Data Shape:** config arrays hold constructors OR descriptors `{plugin, options}`; `renderer` defaults to `defaultRenderer` whose `.rendering` is an already-resolved promise (headless-safe).

### Decisive source
```ts
this.actions = new DragActions<T, U, V>(this);
this.dragOperation = new DragOperation<T, U>(this);
this.collisionObserver = new CollisionObserver<T, U, V>(this);
this.plugins = [CollisionNotifier, ...plugins];   // force-injected FIRST
// ...
const cleanup = effects(() => {
  const currentModifiers = untracked(() => this.dragOperation.modifiers);
  const managerModifiers = this.modifiers;
  for (const modifier of currentModifiers) {
    if (!managerModifiers.includes(modifier)) {
      modifier.destroy();                          // destroy stale per-op instances
    }
  }
  this.dragOperation.modifiers =
    this.dragOperation.source?.modifiers?.map((modifier) => {
      const {plugin, options} = descriptor(modifier);
      return new plugin(this, options);            // fresh instances per source
    }) ?? managerModifiers;                        // fall back to shared manager set
});
```

**Flow:** constructor builds monitor+registry → actions/operation/collisionObserver → sets `plugins` (CollisionNotifier prepended so user plugins can never shadow or omit it) → the modifier effect re-runs whenever the operation's source or its modifiers list changes, destroying instances not in the manager set and re-instantiating from the new source's descriptors. `destroy()` cancels the cleanup effect first (constructor re-binds `this.destroy` around it), stops any active drag with `{canceled:true}`, destroys modifiers/registry/observer.
**Invariant:** CollisionNotifier is ALWAYS registered before user plugins; per-operation modifier instances are destroyed exactly once when replaced — manager-level modifiers are never destroyed by a drag starting/stopping (pinned by `manager-modifiers.test.ts`).
**Probe:** `packages/abstract/tests/manager-modifiers.test.ts` (:62 prefers draggable over manager modifiers; :155 mid-drag modifier swap destroys exactly 1 instance; :129 manager modifiers survive two drags).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "DragDropManager", name_pattern: "^DragDropManager$", limit: 10 });
```

## Verdict
Adopt the composition order, the force-injected core-plugin slot, and replace-not-append per-operation modifier instantiation; adapt `Customizable` resolution to your config style; omit the defaultRenderer placeholder if your host has a real render scheduler.
