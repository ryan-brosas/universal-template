<!-- capsule-v2 -->
# Compile state & environment API — how do callers wait for per-environment stats and cache bundles keyed off stats identity?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know why reset() swaps the deferred (never resolves stale stats), and why bundle caches are WeakMap-keyed by the stats object with failures uncached.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/compileState.ts:createCompileState` (18–46); `packages/core/src/server/environment.ts:loadBundle` (11–68), `getTransformedHtml` (70–87), `createCacheableFunction` (89–118); wiring in `server/devServer.ts` (119, 134–155, 277–332).
**Signature:** `createCompileState(environmentCount)` → `{reset(index), done(index, stats), wait(index): Promise<Stats>}`; `createCacheableFunction<T>(getter): (stats, entryName, utils) => Promise<T>`.
**Data Shape:** parallel arrays `stats: Array<Stats|undefined>` + `waiters: Deferred[]`; cache `WeakMap<Rspack.Stats, Map<string, Promise<T>>>`.

### Decisive source
```ts
// compileState: reset replaces the pending deferred so early waiters CANNOT resolve with stale stats
reset(index) {
  if (!stats[index]) return;          // no-op if nothing published yet
  stats[index] = undefined;
  waiters[index] = createDeferred();
}
done(index, nextStats) { stats[index] = nextStats; waiters[index].resolve(nextStats); }
async wait(index) {
  const current = stats[index];
  return current ?? waiters[index].promise;   // immediate value or new deferred
}
```
```ts
// cacheable: promise cached under CURRENT stats identity; failures evicted for retry
const promise = Promise.resolve().then(() => getter(stats, entryName, utils))
  .catch((error) => { cachedEntries.delete(entryName); throw error; });
cachedEntries.set(entryName, promise);
```

**Flow:** devServer taps each sub-compiler's watchRun at stage −10000 (comment: "Reset API state before user watchRun hooks can read stale environment stats") to call `reset(i)`, and done to call `done(i, stats)`. Environment API methods (`getStats`, `loadBundle`, `getTransformedHtml`) first await `compileState.wait(index)`, then pass the resolved stats into cacheable getters. loadBundle reads entrypoint chunks from `stats.toJson({all:false, chunks, entrypoints, ids, outputPath})`, filters CSS out of chunk files, requires EXACTLY one entry chunk file (throws listing count otherwise), computes all chunk files for `isBundleOutput`, and executes via the vm runner. getTransformedHtml simply reads the html path recorded on the environment context.

**Invariant:** per-environment independence — resolving web's stats must not resolve node's waiter (test 1 asserts nodeResolved stays false); repeated resets must leave earlier waiters permanently pending rather than resolving them with old stats.

**Probe:** `tests/compileState.test.ts:6-28` pins cross-env independence; `:30-53` pins wait-after-reset needing fresh done; `:55-76` pins double-reset never resolving stale. `e2e/cases/server/ssr-load-bundle-external/index.test.ts:10-29` pins ESM default-import parity between loadBundle and native Node import.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "createCompileState createCacheableFunction loadBundle getTransformedHtml", limit: 10 });
```

## Verdict
Adopt deferred-swap-on-reset and stats-identity WeakMap caching with failure eviction for any incremental build server. Adapt the bundle-loading policy (single-entry-chunk rule) to host output shapes. Omit rsbuild's specific toJson field selection beyond what loadBundle needs. Coverage caveat: compileState has direct unit tests; loadBundle path is e2e-only.
