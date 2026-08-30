<!-- capsule-v2 -->
# O(1) LRU with eviction hooks — how does an eviction callback stay correct across delete, clear, and async teardown races?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Where must the eviction hook fire, and why do the async variants remove entries BEFORE awaiting cleanup?

## Delete-then-await async teardown
**Path/Symbol:** `packages/nocodb/src/utils/LRUMap.ts:LRUMap<V>` (whole 103L).
**Signature:** `constructor(maxSize: number, onEvict?: (value: V) => void | Promise<void>)`; get/has/set/delete/clear/asyncDelete/asyncClear; `get size`.
**Data Shape:** plain Map as backing store; insertion order = recency order (delete+re-insert on get promotes).

### Decisive source
```ts
// Removes the entry from the map BEFORE awaiting onEvict so concurrent
// get(key) calls during teardown can't return a value whose cleanup is
// already in progress.
async asyncDelete(key: string): Promise<boolean> {
  const value = this.map.get(key);
  const deleted = this.map.delete(key);
  if (value !== undefined && this.onEvict) {
    await this.onEvict(value);
  }
  return deleted;
}
```
(:70–:81)

**Flow:** get() promotes by delete+set (Map preserves insertion order, so keys().next().value IS the LRU victim); set() evicts the FIRST key when at capacity — firing onEvict synchronously (promise NOT awaited on this path) before inserting → delete()/clear() fire onEvict for removed values when a hook is configured → asyncDelete/asyncClear snapshot-and-remove from the map FIRST, then await each hook, so no reader can observe a value whose resource release already started.
**Invariant:** every removal path must invoke the eviction callback exactly once — capacity eviction, explicit delete, and clear alike — or pooled resources leak. The sync paths fire-and-forget the hook's promise (documented contract), while intentional shutdown uses the async variants and must tolerate awaiting per-value cleanup sequentially. `undefined` values cannot be cached (promotion check is `value !== undefined`).
**Probe:** `cd packages/nocodb && grep -c "this.map.delete(key)" src/utils/LRUMap.ts` (=4: get-promote + set-evict-prep + delete + none-other) and `grep -c "onEvict" src/utils/LRUMap.ts` (=15 incl comments/signatures).
**Direct test:** none upstream for utils/LRUMap.ts — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "LRUMap asyncDelete onEvict maxSize", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt Map-order LRU + universal eviction hooks + remove-before-await teardown; adapt maxSize policy to your memory budget; omit if your runtime has a battle-tested LRU with hooks. Coverage caveat: grep-pinned only.
