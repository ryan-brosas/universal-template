<!-- capsule-v2 -->
# Entity registry — copy-on-write reactive maps with per-entity effect lifetimes

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How does registration stay reactive for subscribers but mutation-safe against re-entrancy, and who cleans up entity effects?

## EntityRegistry
**Path/Symbol:** `packages/abstract/src/core/entities/entity/registry.ts:11-121` (`EntityRegistry`); consumed via `DragDropRegistry.register` dispatcher (manager/registry.ts:76-98).
**Signature:** `register(key, value): () => void` (arrow field — stable identity for effect deps); `unregister(key, value)`; iteration: `[Symbol.iterator]()` uses `map.peek().values()` (NON-tracking) while `.value` returns tracking values.
**Data Shape:** `signal<Map<id, T>>` replaced by immutable copies on every mutation; `WeakMap<T, () => void>` holds each entity's combined effects cleanup.

### Decisive source
```ts
public register = (key, value) => {
  const current = this.map.peek();               // read WITHOUT subscribing
  if (current.get(key) === value) return unregister;
  // ...cleanup previous occupant at this key...
  const updatedMap = new Map(current);
  // Remove ghost registrations: stale entry at a DIFFERENT key for same instance
  for (const [existingKey, existingValue] of current) {
    if (existingValue === value && existingKey !== key) {
      updatedMap.delete(existingKey);
      break;
    }
  }
  updatedMap.set(key, value);
  this.map.value = updatedMap;                   // single reactive publish
  const cleanup = effects(...value.effects());   // entity-scoped effect bundle
  this.cleanupFunctions.set(value, cleanup);
  return unregister;
};

public unregister = (key, value) => {
  const current = this.map.peek();
  if (current.get(key) !== value) return;        // value-guarded no-op
  ...
};
```

**Flow:** register = peek (no tracking) → sweep ghost key → publish new Map once → run the entity's effects() bundle and remember its cleanup. unregister = verify the exact instance still sits at the key (a re-registration at the same key must not be undone by a stale cleanup) → run cleanup → publish removal. `destroy()` iterates via peek, runs every cleanup, then empties.
**Invariant:** mutations NEVER read through the tracked getter (would create an effect-dependency loop); exactly one Map publication per register/unregister; an entity's effects are alive precisely while it is registered. The ghost-sweep matters because Entity id-swaps can leave the old key populated when re-registering under the new one.
**Probe:** `packages/abstract/tests/plugin-registry.test.ts` pins the PluginRegistry twin (same lifecycle shape); EntityRegistry itself is exercised by `drag-event-order.test.ts` register/destroy paths; no dedicated upstream unit file (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "EntityRegistry", name_pattern: "^EntityRegistry$", limit: 10 });
```

## Verdict
Adopt peek-mutate-publish + WeakMap effect ownership + value-guarded unregister for any reactive keyed collection; adapt to your signals library (any with untracked/batch equivalents); omit the ghost sweep only if identities can never change.
