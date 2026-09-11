<!-- capsule-v2 -->
# Autocomplete LRU cache — prefix-keyed SQLite-persisted cache with longest-match retrieval

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does Continue cache completions so identical contexts hit without an LLM call, and how does it handle prefix growth (the user keeps typing) and SQLite persistence?

## The LRU cache
**Path/Symbol:** `core/autocomplete/util/AutocompleteLruCache.ts` (whole, 227L).
**Signature:** `class AutocompleteLruCache` with `static get(): Promise<AutocompleteLruCache>`, `get(prefix): Promise<string|undefined>`, `put(prefix, completion): Promise<void>`, `flush()`, `close()`.
**Data Shape:** in-memory `Map<string, CacheEntry>` (key=truncated prefix, value=completion, timestamp); `capacity=1000`; `flushInterval=30000`; SQLite table `cache(key TEXT PRIMARY KEY, value TEXT NOT NULL, timestamp INTEGER NOT NULL)`; `Mutex` for thread-safety.

### Decisive source
```ts
async get(prefix: string): Promise<string | undefined> {
  const truncatedPrefix = truncateSqliteLikePattern(prefix);
  let bestMatch = null;
  for (const [key, entry] of this.cache.entries()) {
    if (truncatedPrefix.startsWith(key)) {          // longest cached prefix the query starts with
      if (!bestMatch || key.length > bestMatch.key.length) bestMatch = {key, entry};
    }
  }
  if (bestMatch && bestMatch.entry.value.startsWith(truncatedPrefix.slice(bestMatch.key.length))) {
    bestMatch.entry.timestamp = Date.now();          // LRU touch
    this.dirty.add(bestMatch.key);
    return bestMatch.entry.value.slice(truncatedPrefix.length - bestMatch.key.length); // strip matched portion
  }
  return undefined;
}
async put(prefix, completion) {
  const release = await this.mutex.acquire();
  const truncatedPrefix = truncateSqliteLikePattern(prefix);
  try {
    this.cache.set(truncatedPrefix, {value: completion, timestamp: Date.now()});
    this.dirty.add(truncatedPrefix);
    if (this.cache.size > AutocompleteLruCache.capacity) { /* evict oldest by timestamp */ }
  } finally { release(); }
}
async flush() { /* BEGIN TRANSACTION; upsert dirty keys or DELETE evicted; COMMIT / ROLLBACK on error */ }
```

**Flow:** singleton via `static get()` (opens SQLite, `PRAGMA busy_timeout=3000`, creates table, loads all rows into memory, starts a 30s flush timer). `get` uses **longest-match**: finds the longest cached key that the query starts with, validates the cached value starts with the remaining query text, returns the value with the matched portion stripped, and touches the timestamp. `put` truncates the prefix for SQLite pattern safety, upserts, and evicts the oldest entry past capacity. `flush` persists dirty keys in one transaction (upsert for present, delete for evicted), rolling back on error. `close` stops the timer, flushes, closes the DB, and resets the singleton.

**Invariant:** the cache key is the **truncated pruned prefix** (the exact string sent as FIM prefix), so identical contexts hit without an LLM call; retrieval strips the already-matched prefix text so the returned completion is only the NEW suffix; eviction is by oldest timestamp; persistence is batched (dirty-set) not per-write.

**Probe:** `core/autocomplete/util/AutocompleteLruCache.test.ts` (650L) — `put()` stores/marks-dirty/updates/handles-prefix/acquires-mutex; `get()` retrieves-exact-match, longest-match, strips matched prefix, returns undefined on no match.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "AutocompleteLruCache get put flush", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the longest-match prefix-keyed retrieval, the truncated-prefix key, the dirty-set batched SQLite flush, and the oldest-timestamp eviction; adapt the capacity/flush-interval/DB path to host; omit nothing portable. Coverage caveat: graph metadata `metadata_match`; direct test suite.
