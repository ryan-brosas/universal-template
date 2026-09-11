<!-- capsule-v2 -->
# workspace-promise-memoizer

## Source
- Repo: `twenty-crm`
- Path: `packages/twenty-server/src/engine/twenty-orm/storage/promise-memoizer.storage.ts`
- Symbol: `PromiseMemoizer.memoizePromiseAndExecute`
- Lines: 28-76 (whole method; class 21-128)
- Commit: `a6eedd8bf2afad74b6c9a68c9ccaa06d3ce753a0`
- Graph Node: `ext-twenty-crm.packages.twenty-server.src.engine.twenty-orm.storage.promise-memoizer.storage.PromiseMemoizer`

## Signature & Data Shape
```typescript
type AsyncFactoryCallback<T> = () => Promise<T | null>;

type PromiseMemoizerEntry<T> =
  | { state: 'pending'; generation: symbol; promise: Promise<T | null> }
  | { state: 'resolved'; value: T; expiresAt: number };

export class PromiseMemoizer<T> {
  memoizePromiseAndExecute(
    cacheKey: CacheKey,             // string (prefix-scannable)
    factory: AsyncFactoryCallback<T>,
    onDelete?: (value: T) => Promise<void> | void,
  ): Promise<T | null>;
}
```

## Decisive Source Excerpt
```typescript
const newPromise = (async () => {
  try {
    const value = await factory();
    const currentEntry = this.cache.get(cacheKey);
    if (
      value &&                                  // null NEVER cached
      currentEntry?.state === 'pending' &&
      currentEntry.generation === generation     // MY invocation still owns the slot
    ) {
      this.cache.set(cacheKey, {
        state: 'resolved',
        value,
        expiresAt: Date.now() + this.ttlMs,
      });
    }
    return value;
  } finally {                                    // NOT catch — runs on success AND failure
    const currentEntry = this.cache.get(cacheKey);
    if (
      currentEntry?.state === 'pending' &&
      currentEntry.generation === generation
    ) {
      this.cache.delete(cacheKey);               // only delete if I still own the slot
    }
  }
})();
this.cache.set(cacheKey, { state: 'pending', generation, promise: newPromise });
return newPromise;
```

## Flow
1. `clearExpiredKeys(onDelete)` sweeps resolved-expired entries (awaiting each `onDelete`) BEFORE every lookup.
2. Existing entry? Return cached `value` (resolved+unexpired) or join in-flight `promise` (pending) — concurrent callers collapse onto one factory run.
3. Miss → mint `const generation = Symbol()` and store `{state:'pending', generation, promise}`.
4. On factory resolution the pending→resolved promotion is gated on **both** truthiness of `value` and generation identity; a stale or nulled result returns to its caller but never poisons the cache.
5. In the **generation-guarded `finally`**, the key is deleted ONLY when the settling invocation still owns the slot. If `clearKey`/`delete` ran mid-flight (slot gone) or another invocation replaced it (generation mismatch), the loser leaves the cache untouched.

## Invariant
Concurrent async factories collapse onto one pending promise, and EVERY cache mutation after `await` is generation-checked: late-resolving losers must not overwrite newer winners, and a rejected factory must NOT wipe a slot that invalidation already handed to a newer invocation. Null results are returned but never cached. This is the exact trap a porter falls into by writing `catch { cache.delete }` — that variant lets a slow failed hydration destroy a fresh entry installed between failure and cleanup.

## Direct-Test Probe
- File: `packages/twenty-server/src/engine/twenty-orm/storage/__tests__/promise-memoizer.storage.spec.ts`
- Suite: `describe('PromiseMemoizer')` (:3) / `describe('memoizePromiseAndExecute')` (:28)
- Pin: `it('should not cache a stale promise after its key is cleared')` (:141)

```bash
grep -c "should deduplicate concurrent requests\|should not cache a stale promise" packages/twenty-server/src/engine/twenty-orm/storage/__tests__/promise-memoizer.storage.spec.ts   # => 2
grep -n "} finally {" packages/twenty-server/src/engine/twenty-orm/storage/promise-memoizer.storage.ts   # => 1 hit :57
```

## Graph Query
```bash
echo '{"project":"ext-twenty-crm","name_pattern":"PromiseMemoizer"}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt for any per-workspace/per-schema hydration cache. The generation-symbol + guarded-finally pair is the load-bearing detail; both must be ported together or the cache loses entries under invalidation races.
