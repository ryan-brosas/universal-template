<!-- capsule-v2 -->
# Signals toolkit — @reactive accessor, @derived getter, ValueHistory, WeakStore

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** Which tiny primitives does the kernel assume, and what are their exact semantics (peek vs track, equality, reset)?

## @dnd-kit/state core
**Path/Symbol:** `packages/state/src/decorators.ts:5-46` (`reactive`, `derived`), `history.ts:11-76` (`ValueHistory`), `store.ts:1-22` (`WeakStore`), `computed.ts:6-26` (`computed` w/ comparator), `effects.ts` (`effects(...fns): CleanupFunction`), `snapshot.ts`.
**Signature:** `@reactive` = accessor decorator wrapping a `signal(value)` with `peek()`-equality setter guard; `@derived` = getter decorator memoizing a `computed` per instance in a WeakMap; `ValueHistory(defaultValue, equals)` exposes `{current, initial, previous}` + `reset()`; `WeakStore<WeakKey, Key, Value>` = WeakMap→Map two-level get/set/clear.
**Data Shape:** all reactive state is preact-signals-core under the hood; `batch()` groups writes; `untracked()` reads without subscribing.

### Decisive source
```ts
// decorators.ts — setter dedupe is PEEK-based (no subscription created by writing)
set(newValue: Value) {
  const current = get.call(this) as Signal<Value>;
  if (current.peek() === newValue) return;   // reference equality!
  current.value = newValue;
}

export function derived(target, _) {
  const map: WeakMap<any, Signal<Return>> = new WeakMap();
  return function (this) {
    let result = map.get(this);
    if (!result) { result = computed(target.bind(this)); map.set(this, result); }
    return result.value;
  };
}

// history.ts — initial is captured ONCE per cycle
public set current(value: T) {
  const current = untracked(() => this.#current);
  if (value && current && this.equals(current, value)) return;   // equals = Object.is default
  batch(() => {
    if (!this.#initial) this.#initial = value;
    this.#previous = current;
    this.#current = value;
  });
}
```

**Flow:** classes declare `accessor x` fields → decorator swaps storage to a signal at init → reads subscribe, writes dedupe via peek. Getters marked `@derived` lazily build one computed signal PER INSTANCE (WeakMap keyed on `this`) so identical instances share cache and dead instances are GC-able. DragOperation uses ValueHistory for shape (`equals = Shape.equals`) giving `{current, initial, previous}` needed by drop animations; Sortable keeps TemporaryState in a manager-keyed WeakStore so the same sortable under two managers stays isolated.
**Invariant:** `@reactive` equality is REFERENCE equality (Object.is) — callers must replace objects, never mutate them (this is why registries copy Maps); derived getters must not self-reference or the computed loop-throws; `snapshot(obj)` iterates keys inside untracked to materialize plain data for events.
**Probe:** `packages/state/tests/comparators.test.ts` pins `deepEqual` (arrays/sets/key-order-insensitive objects, functions by reference) used as the comparator twin; live suite GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "ValueHistory WeakStore", name_pattern: "^ValueHistory$", limit: 10 });
```

## Verdict
Adopt the four primitives wholesale (they total <300 lines); adapt the signals backend to your library keeping peek/track/batch semantics; omit ValueHistory only if your consumers never need initial-vs-current comparisons.
