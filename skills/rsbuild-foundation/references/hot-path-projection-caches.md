<!-- capsule-v2 -->
# Hot-path projection caches — how does the SSR/HTML request path avoid re-deriving per-entry data on EVERY request without leaking compilations?

**Source:** rsbuild MIT `main@bc19fd5e`; Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild` (path-slugged twin adopted 2026-08-24). **Question:** a porter must know the three stacked caches (stats projection WeakMap, lazily-materialized outputFilePaths Set, promise memo per stats+entry) and why failures are never cached.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/environment.ts` — `loadBundleStatsCache` (19), materialization in `loadBundle` (26–37, 78–87), runner handoff (89–96); `createCacheableFunction` (122–159); dev-side wiring `server/devServer.ts` (285–291, 346–368). Perf-cluster commits: f1afbf7 (projection cache), fc57410 (Set-based file lookup), 64c8af5+3421cf2 (manifest maps), 6247289+412a159 (hint collection/dedupe), 8d473d1 (deferred tag sort).
**Signature:** `loadBundle<T>(stats, entryName, utils): Promise<T>`; `createCacheableFunction<T>(getter): (stats, entryName, utils) => Promise<T>`.
**Data Shape:** `WeakMap<Rspack.Stats, LoadBundleStats>` where `LoadBundleStats = Pick<StatsCompilation,'chunks'|'entrypoints'|'outputPath'> & {outputFilePaths?: Set<string>}`; cache-of-cache `WeakMap<Stats, Map<string, Promise<T>>>`.

### Decisive source
```ts
// Layer 1 — one toJson() per COMPILATION, not per request (entries share it):
let loadBundleStats = loadBundleStatsCache.get(stats);
if (!loadBundleStats) {
  loadBundleStats = { ...stats.toJson({ all:false, chunks:true, entrypoints:true, ids:true, outputPath:true }) };
  loadBundleStatsCache.set(stats, loadBundleStats);
}
// Layer 2 — outputFilePaths materialized ONCE per compilation as a Set (was O(n) includes()):
let { outputFilePaths } = loadBundleStats;
if (!outputFilePaths) {
  outputFilePaths = new Set<string>();
  for (const chunk of chunks || [])
    for (const file of chunk.files!) outputFilePaths.add(join(outputPath!, file));
  loadBundleStats.outputFilePaths = outputFilePaths;
}
const res = await run<T>({ bundlePath: files[0], dist: outputPath!,
  compilerOptions: stats.compilation.options, readFileSync: utils.readFileSync,
  isOutputFile: (modulePath) => outputFilePaths.has(modulePath) });   // O(1)
```
```ts
// Layer 3 — pending PROMISE cached so concurrent requests share one execution;
// failures evicted so the next call retries instead of caching the throw:
const cachedPromise = cachedEntries.get(entryName);
if (cachedPromise) return cachedPromise;
const promise = Promise.resolve().then(() => getter(stats, entryName, utils))
  .catch((error) => { cachedEntries.delete(entryName); throw error; });
cachedEntries.set(entryName, promise);
return promise;
```

**Flow:** every environment-API call awaits `compileState.wait(index)` FIRST (fresh-stats gate, see `compile-state-env-api`), then hits layer 3 keyed by (stats identity, entryName); the getter itself consults layers 1–2. Same-family optimizations elsewhere in the drift: manifest builds `filePathByName` Map once during the files walk and replaces `files.find(f => f.name === …)` with O(1) `.get()` plus push-don't-rebuild entry grouping (`plugins/manifest.ts` 34–56, 126); resource hints collect files into ONE pass over chunks with a Set for dedupe and hoist `scriptSources` to a memoized `ReadonlySet` built at most once across dedupe groups (`rspack-plugins/resource-hints/HtmlResourceHintsPlugin.ts` 125–160, 196–215); RsbuildHtmlPlugin defers tag sorting to run ONCE after the loop (flush before any function-config so function tags receive sorted input) instead of re-sorting per appended tag (`rspack-plugins/RsbuildHtmlPlugin.ts` 106–110, 209–231).

**Invariant:** (1) ALL layers key off the STATS OBJECT identity via WeakMap — old compilations are GC-able the moment watchRun resets compileState; nothing retains a dead compilation; (2) a rejected promise must EVICT itself — caching the rejection would turn one transient read failure into a permanent 500 for that entry until next rebuild; (3) concurrent callers share the in-flight promise (single-flight), never two parallel vm executions of the same bundle; (4) `isOutputFile` gates which modules the vm requirer loads from disk vs. treats as external — deriving it from a stale compilation's file set would execute WRONG module bytes.

**Probe:** `e2e/cases/server/ssr-load-bundle-external/index.test.ts:10-29` (loadBundle result parity with native import through the full cache stack); `e2e/cases/server/load-bundle-cjs-native-import/index.test.ts:4-17` (CJS bundle + native import() through same path); unit layer for createCacheableFunction itself is absent at pin — its failure-eviction/single-flight contract is pinned by `compile-state-env-api`'s compileState tests (`packages/core/tests/compileState.test.ts`) covering the surrounding wait/reset machinery.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "createCacheableFunction loadBundleStatsCache outputFilePaths filePathByName scriptSources sortTags", limit: 10 });
```

## Verdict
Adopt the identity-keyed WeakMap layering, lazy Set materialization replacing linear includes(), single-flight promise caching with self-evicting failures, and deferred single-sort flush-before-function-tags. Adapt cache granularity to your host's stats object shape. Omit rsbuild's specific toJson field whitelist if your stats shape differs. Coverage caveat recorded above.
