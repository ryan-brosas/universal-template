<!-- capsule-v2 -->
# Entity id batching — how do virtualized id swaps avoid registry collisions?

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** Why can't `entity.id = newId` write the signal directly when two entities swap ids in one frame?

## Microtask-batched atomic id changes
**Path/Symbol:** `packages/abstract/src/core/entities/entity/entity.ts:48-134` (`Entity.pendingIdChanges`, `#flushIdChanges`, id getter/setter).
**Signature:** `static pendingIdChanges: Map<Entity, UniqueIdentifier> | null`; setter parks writes; getter reads pending-first: `Entity.pendingIdChanges?.get(this) ?? signalValue`.
**Data Shape:** static Map keyed by entity instance → new id; null when idle; flushed by a single `queueMicrotask` that applies all writes inside one `batch()`.

### Decisive source
```ts
public set id(value: UniqueIdentifier) {
  const current = Entity.pendingIdChanges?.get(this) ?? this.#idSignal.peek();
  if (value === current) return;

  if (!Entity.pendingIdChanges) {
    Entity.pendingIdChanges = new Map();
    queueMicrotask(() => Entity.#flushIdChanges());   // ONE flush for N writes
  }

  Entity.pendingIdChanges.set(this, value);
}

static #flushIdChanges() {
  const changes = Entity.pendingIdChanges;
  Entity.pendingIdChanges = null;
  if (changes) {
    batch(() => { for (const [entity, id] of changes) entity.#idSignal.value = id; });
  }
}
```

**Flow:** first id write arms the microtask + creates the map → subsequent same-tick writes just park → microtask nulls the map THEN batch-applies every signal write. The id-change effect inside each entity (:78-92) then re-registers at the new key and unregisters the old — but because all signals flip inside one batch, no observer ever sees A and B holding the same id.
**Invariant:** readers between setter and flush MUST see the pending value (getter consults the map) or sorting logic would resolve stale ids mid-swap; CollisionNotifier explicitly checks `Entity.pendingIdChanges` and skips dispatch while a swap is in flight (notifier.ts:36-38) — dropping that check reintroduces ghost targets during sortable swaps.
**Probe:** deterministic: setter/getter round-trip through a lifted copy of this class shape; upstream coverage is via sortable integration tests (`optimistic-sorting-plugin.test.ts` exercises index/group mutation paths); direct unit test for the static batching itself does not exist upstream (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "pendingIdChanges", name_pattern: "Entity", limit: 10 });
```

## Verdict
Adopt pending-map + single-flush batching for ANY identity-keyed reactive collection that supports reordering; adapt flush timing to your scheduler (microtask ≈ sync batch boundary); omit only if your ids are immutable per instance.
