<!-- capsule-v2 -->
# Queue/cache decorators — how do I serialize source actions against an account and cache read methods with generation-safe invalidation?

**Source:** lh-basis (Linked Helper extract) **NO LICENSE — learn-only, patterns recorded, zero code copied**; Codebase Memory `lh-basis-source` (root `…/core/local-source/dist/Source`). **Question:** how does a production LinkedIn-automation core guarantee one-action-at-a-time per account and cache `get*` methods that invalidate on writes?

## queued + cache/CacheManager decorator pair
**Path/Symbol:** `decorators/queued.js:queued` (minified factory); `decorators/cache.js:cache` + `CacheManager` (handleCache, clearCacheIfNeeded, saveToCache).
**Signature:** `queued(target, name, descriptor)` wraps the method: reads `decoratorSettings.queueEnabled` → either `execInQueue(fn)` or direct await; `cache({prepareArgs, prepareResultToCache, restoreResult, getExpirationDate, shouldCacheResult, preventCacheClear})` registers metadata via Reflect.
**Data Shape:** queue telemetry record `{name:"Class:method()", queuedAt, startedAt, endedAt, perfReport}` keyed by the SOURCE INSTANCE in `currentQueuedBySource`; cache row `{liAccountId, method, args(JSON-stringified), result, expiresAt}` plus a per-source `generation` counter.

### Decisive source
```js
// queued: every wrapped action is timed, reported, and serialized per account
r.value = async function (...args) {
    const src = getSourceInstance(this);
    const o = async () => {
        currentQueuedBySource.set(src, { name: `${this.constructor.name}:${String(t)}()`, … });
        try { return await u.apply(this, args); }
        finally { r.addPerformanceReportItem(name, hrtime-delta, {arguments, returnValue});
                  currentQueuedBySource.delete(src); }        // ALWAYS cleared — even on throw
    };
    return r.decoratorSettings.queueEnabled ? r.execInQueue(o) : await o();
};
// CacheManager.isWriteMethod: read-prefix allowlist decides invalidation
isWriteMethod() { return !this.readMethodPrefixes.some(p => this.methodName.includes(`:${p}`)); }
// prefixes: ["get","is","are","check","export","prev","fetch"]
```

**Flow:** any Source method call → queued wrapper enqueues per source-instance (one account's actions never interleave) and records performance → CacheManager.handleCache on read-prefixed methods: prepare args → lookup (liAccount+method+args) → hit ⇒ restore via custom deserializer; miss ⇒ run original inside a savepoint → shouldCacheResult may reject → save with expiration under the CURRENT generation.
**Invariant:** write methods bump the generation counter and delete cached rows (`clearCacheIfNeeded`) so stale reads can't survive a mutation; every cache failure path returns `{result:null, cacheBypassed:true}` — caching is best-effort and NEVER breaks the underlying call; queue slot always released in `finally`.
**Probe:** no public tests (proprietary extract) — coverage caveat recorded. Graph anchors resolve in `lh-basis-source`: `decorators.cache.CacheManager`, `MethodCallCacheManagerFactory`, `Source.currentQueued`; coverage check reports `no_recorded_issue`+`metadata_match` for both decorator files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis-source", query: "CacheManager", limit: 5 });
```

## Verdict
Adopt the contract shapes: per-account action queues with finally-released telemetry slots, and generation-counter cache invalidation driven by a read-prefix allowlist; adapt to your DI/framework (these are legacy-node Reflect.metadata decorators); omit nothing conceptually but re-implement from scratch — **this repo carries no license, so no code may be copied**.
