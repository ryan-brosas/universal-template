<!-- capsule-v2 -->
# splitChunks strategy dispatcher + preset ladder — why does per-package name() win at negative priority?

**Source:** rsbuild MIT `main@bc19fd5e` (pass-3 repair: server default flipped from off to preset-based by c165817); Codebase Memory `mnt-hdd-utopia-inspo-frameworks-rsbuild` (path-slugged twin adopted 2026-08-24). **Question:** a porter must reproduce the six legacy strategies, the new preset switch, and the SPLIT server / OFF worker defaults.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/splitChunks.ts` — `getForceSplittingGroups` 22–44 (priority 1 under single-vendor, enforce:true), presets 46–93, strategies 95–181, MODULE_PATH_REGEX 108–109 + `getPackageNameFromModulePath` 111–120 (pnpm `.pnpm/` negative-lookahead), dispatcher 211–218, plugin 250–305 (webWorker eager dynamicImportMode 257–264, server/worker branch 266–278, legacy-vs-new arbitration 280–304).
**Signature:** `makeLegacySplitChunksOptions(chunkSplit, config, rootPath)`; `getSplitChunksByPreset(config, preset)`.
**Data Shape:** strategies: all-in-one(false)|split-by-experience|split-by-module|split-by-size|single-vendor|custom; cacheGroups spread ORDER = base → force → override.

### Decisive source
```ts
function resolvePerPackagePreset() {
  return { minSize: 0, maxInitialRequests: Number.POSITIVE_INFINITY,
    cacheGroups: { vendors: { priority: -9, test: NODE_MODULES_REGEX,
      name(module) { return module ? getPackageNameFromModulePath(module.context!) : undefined; } } } };
}
```
```ts
// SERVER builds (pass-3 REPAIR — c165817 flipped the default): preset-based split, chunks:'all'
if (isServer) {
  if (splitChunks === false) chain.optimization.splitChunks(false);
  else { const { preset = 'none', ...rest } = splitChunks;
    chain.optimization.splitChunks({ chunks: 'all', ...getSplitChunksByPreset(config,preset), ...rest }); }
  return;
}
// WEB WORKER builds stay DEFAULT-OFF (no dynamic import support):
if (isWebWorker) {
  if (splitChunks === false || Object.keys(splitChunks).length === 0) chain.optimization.splitChunks(false);
  else { const { preset = 'none', ...rest } = splitChunks; chain.optimization.splitChunks({ ...getSplitChunksByPreset(config,preset), ...rest }); }
  return;
}
// web: legacy performance.chunkSplit honored ONLY while new API untouched:
if (chunkSplit && splitChunks !== false && Object.keys(splitChunks).length === 0) { ...legacy...; return; }
```

**Flow:** force groups get enforce:true so minSize/maxRequests never block them; under single-vendor they take priority 1 to beat the vendor catch-all. split-by-experience = web defaults + polyfill lib-polyfill group (tslib/core-js/@swc/helpers) + force + override. moduleFederation provider apps flip chunks:'async' so remote entries stay intact. Unknown preset names throw loudly. Server environments now split by default with `chunks:'all'` and preset 'none' escape hatch — the empty-config snapshot pins `{splitChunks:{chunks:'all'}}` for node targets (`environments.test.ts.snap` node block), while workers keep `false`.
**Invariant:** (1) override.cacheGroups spreads LAST — user groups can shadow built-ins by key reuse; (2) name() returning undefined lets rspack fall back to default naming instead of crashing; (3) pnpm layouts need the `(?!\\.pnpm[\\/])` guard or every package resolves to ".pnpm"; (4) server/worker defaults DIVERGE: server splits (preset 'none' ⇒ bare `chunks:'all'`), worker stays off unless explicitly configured.
**Probe:** unit `packages/core/tests/splitChunks.test.ts:41` (preset single-vendor), :89–131 describe('getPackageNameFromModulePath') npm/yarn/pnpm matrix incl. scoped names. Snapshot `packages/core/tests/__snapshots__/environments.test.ts.snap:1064-1069` pins the server flip (`"splitChunks": {"chunks": "all"}` where pre-c165817 read `"splitChunks": false`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-rsbuild", query: "pluginSplitChunks getPackageNameFromModulePath resolveSingleVendorPreset makeLegacySplitChunksOptions", limit: 8 });
```

## Verdict
Adopt the dispatcher shape, enforced force-groups, per-package negative-priority naming, MF async flip, server preset-based split with `chunks:'all'` (post-c165817), and worker default-off. Adapt group keys and regexes to host package manager. Omit deprecated chunkSplit surface unless migrating users.
