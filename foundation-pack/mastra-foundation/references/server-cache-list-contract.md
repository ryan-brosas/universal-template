<!-- capsule-v2 -->
# server-cache list contract — what minimal cache interface does resumable streaming need, and what are the in-memory reference semantics?

**Source:** mastra Apache-2.0 `main@3d2ff0d0a959792331f7cfb12dab6d08506676e7`; Codebase Memory `ext-mastra`. **Question:** What is the smallest async cache abstraction that supports chunk-replay streams and event indexing, and how does the TTL-backed in-memory implementation handle lists, counters, and TTL overrides?

## Seven-method cache surface + TTL-normalizing list/counter store
**Path/Symbol:** `packages/core/src/cache/base.ts` : `MastraServerCache` (:3-41); `packages/core/src/cache/inmemory.ts` : `InMemoryServerCache` (:21-118).
**Signature:**
```typescript
abstract class MastraServerCache extends MastraBase {
  get(key): Promise<unknown>; set(key, value, ttlMs?): Promise<void>;
  listLength(key): Promise<number>; listPush(key, value): Promise<void>;
  listFromTo(key, from, to?): Promise<unknown[]>;    // Redis LRANGE semantics
  delete(key): Promise<void>; clear(): Promise<void>;
  increment(key): Promise<number>;                   // atomic counter, first call → 1
}
```
**Data Shape:** values are untyped (`unknown`) — the same key namespace serves singletons (replay offsets via `increment`), arrays (chunk history via `listPush/listFromTo`), and numbers (counters). Type errors are LOUD: pushing to a non-array or incrementing a non-number throws `` `${key} exists but is not an array|number` ``.

### Decisive source
```typescript
async set(key, value, ttlMs?) {
  if (ttlMs === undefined) return void this.cache.set(key, value);
  // TTLCache requires positive integer or Infinity; non-positive overrides
  // mean "no expiry" and must be normalized.
  this.cache.set(key, value, { ttl: ttlMs > 0 ? ttlMs : Infinity });
}
async listFromTo(key, from, to = -1) {
  const list = this.cache.get(key) as unknown[];
  if (Array.isArray(list)) {
    // Make 'to' inclusive like Redis LRANGE - add 1 unless it's -1
    const endIndex = to === -1 ? undefined : to + 1;
    return list.slice(from, endIndex);
  }
  return [];                       // missing key ⇒ empty list, never throw
}
```

**Flow:** `listPush` on existing array mutates + re-sets with refreshed default TTL (active streams don't expire mid-flight); missing key creates `[value]`; wrong type throws. Defaults: maxSize 1000, ttl 5 min; ttl 0 disables expiry (normalized to Infinity). `increment` starts at 1 — documented as the sequential event-index generator for distributed (Redis INCR) implementations.
**Invariant:** Missing-key reads degrade (`get`→undefined, `listFromTo`→[], `listLength`→0) but WRONG-TYPE keys always throw — silent zero would hide corruption. Per-key TTL overrides normalize non-positive → never-expire. The abstract docstrings pin Redis as the distributed reference semantics (INCR atomicity, LRANGE inclusivity).
**Probe:** `packages/core/src/cache/inmemory.test.ts`: get/set matrix incl. overwrite (:44), `should not throw when deleting non-existent key` (:61), List Operations suite (:85+ — create-on-push, append, mixed types).
**Coverage caveat:** TTL-refresh-on-push and increment-first-is-1 behavior verified by reading source at this pin; dedicated test lines for those two paths not enumerated in the visible suite listing — treat as source-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "MastraServerCache InMemoryServerCache listPush increment listFromTo", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the seven-method surface as the porting seam for any resumable-stream cache backend; adopt loud type-mismatch throws + quiet missing-key reads. Adapt storage (Redis/Upstash behind identical methods). Omit nothing in base.ts — it is already minimal. Porters who make list reads throw on missing keys break reconnect-after-TTL flows; who treat `to=-1` as exclusive produce off-by-one replay windows.
