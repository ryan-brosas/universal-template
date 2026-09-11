<!-- capsule-v2 -->
# require(esm) sync graph walker — how can a synchronous require() resolve an ES module graph without poisoning the cache on failure?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b3`); Codebase Memory `vitest`. **Question:** How does `require()` of an ESM file mirror Node 24.9+ semantics inside a vm, and what cache-commit rule keeps a failed require from breaking a later import()?

## Scratch-map collect → link → commit-once walker
**Path/Symbol:** `packages/vitest/src/runtime/vm/esm-executor.ts:EsmExecutor.requireEsModuleSync` (:208–323), `reuseSyncModule` (:329–352), `ScratchEntry` union (:23–26).
**Signature:** `public requireEsModuleSync(rootIdentifier: string): VMModule`; `private reuseSyncModule(identifier: string, cached: VMModule | Promise<VMModule>): VMModule`.
**Data Shape:** `ScratchEntry = { module; deps?: undefined; commit: boolean } | { module: VMSourceTextModule; deps: string[]; commit: true }` — `deps` present DISCRIMINATES source-text modules the walk built (linkable) from complete modules (cache hits, synthetic/json); `commit=false` for anything the walk does not own. The executor's `moduleCache` maps identifier → settled `VMModule` OR in-flight `Promise<VMModule>`.

### Decisive source
```ts
const scratch = new Map<string, ScratchEntry>()
const worklist: string[] = [rootIdentifier]
while (worklist.length > 0) {
  const identifier = worklist.pop()!
  if (scratch.has(identifier)) continue
  const cached = this.moduleCache.get(identifier)
  if (cached) { scratch.set(identifier, { module: this.reuseSyncModule(identifier, cached), commit: false }); continue }
  const disposition = /* data-URI or materializeSyncModule */
  ...
  const module = this.createSourceTextModule(identifier, disposition.code)
  if (module.hasTopLevelAwait()) throw createRequireAsyncModuleError(identifier, 'the module uses top-level await')
  ...push resolved dep identifiers...
  scratch.set(identifier, { module, deps, commit: true })
}
// only after the WHOLE graph proved sync-evaluable:
for (const entry of scratch.values()) entry.deps && entry.module.linkRequests(...)
if (root.deps) root.module.instantiate()
...defensive async-graph recheck...
for (const [identifier, entry] of scratch) {
  if (entry.commit && !this.moduleCache.has(identifier)) this.moduleCache.set(identifier, entry.module)
}
root.module.evaluate().catch(() => {})
```

**Flow:** iterative worklist walk (no recursion) → cached entries are validated by `reuseSyncModule`: Promise = concurrent-import error, errored = rethrow its error, non-evaluated = concurrent error, async-graph = TLA error → fresh modules reject top-level-await PER MODULE during the walk → after full collection, links are made root-down, instantiate runs, and ONLY THEN do owned (`commit:true`) entries land in `moduleCache` → evaluate fulfills synchronously (no TLA anywhere), errors read off `status`/`error`, never off the promise.
**Invariant:** A failed require must leave NO trace in `moduleCache` — commit happens strictly after whole-graph success, so a later dynamic `import()` of the same file starts clean (in-source comment is explicit). Cached modules are reusable by the sync path only when fully SETTLED — a pending Promise or mid-flight evaluation is a concurrency error, not something to await (you cannot await in require). Data-URI twins: wasm refuses sync load, JSON becomes a SyntheticModule. A porter who commits per-module during the walk poisons the cache on any mid-graph failure.
**Probe:** `grep -c 'commit: false' packages/vitest/src/runtime/vm/esm-executor.ts` = 2 (:225/:240) and `'commit: true'` = 3 (:247/:270/:305-arm) — the discriminator sites pin the ownership rule; e2e coverage lives under `test/e2e/test/vm-threads.test.ts` require(esm) blocks. Verified on disk at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "requireEsModuleSync ScratchEntry reuseSyncModule createRequireAsyncModuleError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scratch-collect → validate-cached-settledness → link-after-collect → commit-owned-only-after-success for ANY host adding sync require of ESM graphs. Adapt disposition kinds to your loader's materialization surface. Omit the data-URI/wasm arms only if your host resolves such identifiers before the executor sees them.
