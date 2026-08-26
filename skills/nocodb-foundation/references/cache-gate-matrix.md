<!-- capsule-v2 -->
# Cache bypass vs disable matrix — which cache operations stop when disabled or inside runWithoutCache, and which must still go through?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** Which cache operations stop when globally disabled or inside a transaction-scoped bypass — and why do invalidation and counters still pass through?

## NocoCache gate matrix
**Path/Symbol:** `packages/nocodb/src/cache/NocoCache.ts` (52-353, per-method guards); `packages/nocodb/src/cache/cacheBypassScope.ts:runWithoutCache/isCacheBypassed` (21-24).
**Signature:** `runWithoutCache<T>(fn: () => Promise<T>): Promise<T>`; `isCacheBypassed(): boolean`; every NocoCache static method begins `if (this.cacheDisabled || isCacheBypassed()) return <neutral>`.
**Data Shape:** scope value = literal `true` in AsyncLocalStorage; neutral returns: reads → typed empties (`[]`, `{}`, `null`, `false`, `0`), writes → `true`.

### Decisive source
```ts
// READ/WRITE ops gated on BOTH flags:
public static async get(context, key, type) {
  if (this.cacheDisabled || isCacheBypassed()) {
    if (type === CacheGetType.TYPE_ARRAY) return Promise.resolve([]);
    else if (type === CacheGetType.TYPE_OBJECT) return Promise.resolve(null);
    return Promise.resolve(null);
  } ...
}
// INVALIDATION + COUNTERS gated on cacheDisabled ONLY (bypass does NOT stop them):
public static async del(context, key) {
  if (this.cacheDisabled) return Promise.resolve(true);   // no isCacheBypassed()
  ...
}
public static async incrby(context, key, value) {
  if (this.cacheDisabled) return Promise.resolve(true);
  ...
}
```

**Flow:** `runWithoutCache(fn)` marks only fn's async tree. Inside a DB transaction, reads return empties (forcing the DB as truth for uncommitted state) and writes are swallowed (uncommitted rows must not leak into the shared cache). But deletes/counters still execute so invalidations issued inside the transaction aren't lost — the post-commit cache is consistent with the committed data.
**Invariant:** when adding an op to the facade, classify it: mutations of cached content (`set/setList/appendToList/update/setHash*`) respect bypass; removals (`del/deepDel/delHashField/clear`) and counters (`incrby/incrHashField/incrbyExpiring`) don't. Also note two deliberate quirks: `setIfNotExist`/hash ops skip the bypass check entirely (lock-style semantics must work under transactions), and `setHashField` awaits then returns literal `true` because hset returns *newly added field count*, which would misreport overwrites as failure.
**Probe:** no unit test upstream. Source-grounded probe: grep the facade — exactly `del/deepDel/incrby/incrbyExpiring/incrHashField/delHashField/expireHash/keyExists/processPattern/clear` lack `isCacheBypassed()`; `get/set/setList/getList/appendToList/update/getHash*/setHash*/setExpiring` include it.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "NocoCache isCacheBypassed cacheDisabled runWithoutCache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the read/write-bypass-but-invalidate-through matrix and AsyncLocalStorage scoping; adapt neutral-return types to your read API and decide explicitly whether lock ops bypass; omit RedisMock/Redis manager split (single backend suffices). Coverage caveat: no in-repo tests; source-grounded.
