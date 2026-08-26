<!-- capsule-v2 -->
# Cache bypass — the AsyncLocalStorage scope for DB-transaction cache safety

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3`; Codebase Memory `nocodb`. **Question:** How do you make a shared cache read/write transparently disabled inside a DB transaction (so reads don't see stale pre-transaction state and writes don't leak uncommitted data) without threading a flag through every call?

## Cache bypass scope
**Path/Symbol:** `packages/nocodb/src/cache/cacheBypassScope.ts` (whole file, 24L): `runWithoutCache` / `isCacheBypassed`; consumed by `cache/NocoCache.ts` (get/set/etc. guard on `isCacheBypassed()`).
**Signature:** `runWithoutCache<T>(fn: () => Promise<T>): Promise<T>`; `isCacheBypassed(): boolean`.
**Data Shape:** `const scope = new AsyncLocalStorage<true>()`. Inside the scope, cache reads (`get/getList/getHash/getHashField`) return empty and writes (`set/setList/setExpiring/setHash/setHashField/appendToList/update`) are no-ops; invalidation (`del/deepDel/delHashField/clear`) and counters (`incrby/incrHashField`) pass through unchanged.

### Decisive source
```ts
const scope = new AsyncLocalStorage<true>();
export const runWithoutCache = <T>(fn: () => Promise<T>): Promise<T> =>
  scope.run(true, fn);
export const isCacheBypassed = (): boolean => scope.getStore() === true;
// consumer (NocoCache.ts, ~every op):
if (this.cacheDisabled || isCacheBypassed()) return Promise.resolve(true);  // writes no-op
if (this.cacheDisabled || isCacheBypassed()) return Promise.resolve(null);  // reads empty
```

**Flow:** Callers wrap DB-transaction work in `runWithoutCache(fn)`; every NocoCache op checks `isCacheBypassed()` and short-circuits reads/writes. The scope is per-async-tree via AsyncLocalStorage — concurrent requests outside the scope are unaffected, and nested calls are a safe no-op.

**Invariant:** Invalidation and counters are NEVER bypassed — a transaction that bypasses reads/writes must still be able to invalidate stale cache entries and bump counters. The bypass is per-async-tree, so it cannot leak across concurrent requests. Reads inside the scope must return "empty" (not stale), writes must be dropped (not committed to the shared cache).

**Probe:** No in-repo unit test exists. Source-grounded probe: `grep isCacheBypassed cache/NocoCache.ts` shows the guard on every read/write op (confirmed at lines 53/66/117/150/169/197/210/225/240/251/264) and its absence from the invalidation/counter paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "runWithoutCache isCacheBypassed cacheBypassScope", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the AsyncLocalStorage bypass scope with read/write no-op + invalidation/counter pass-through; adapt the cache API surface. Omit the NocoCache/Redis cache manager internals unless porting the whole cache layer. Caveat: no direct test — source-grounded only.
