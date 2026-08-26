<!-- capsule-v2 -->
# Plugin API surface — how does `api.transform`/`processAssets`/`expose` reach into Rspack compilations per environment?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know why transform/processAssets/resolve are collected into arrays and bridged by ONE core Rspack plugin inside modifyBundlerChain, and how exposed APIs resolve environment-first.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/initPlugins.ts:initPluginAPI` (85–408) — `getNormalizedConfig` overloads (95–116), `getRsbuildConfig` (118–131), expose/useExposed (133–159), RsbuildCorePlugin (174–245), `getTransformHook` (247–311), `setProcessAssets` (313–316), `setResolve` (318–320), onExit latch (322–332).
**Signature:** `initPluginAPI({context, pluginManager}): (environment?: string) => RsbuildPluginAPI`.
**Data Shape:** module-level collectors: `transformer: Record<string /*id*/, TransformHandler>`, `processAssetsFns: {environment?, descriptor, handler}[]`, `resolveFns: {environment?, handler}[]`, `exposed: Map<id, Map<key|GLOBAL_EXPOSED_KEY, api>>`; `transformId` counter mints rule names `rsbuild-transform-N`.

### Decisive source
```ts
// One bridge plugin per compilation carries ALL collected hooks into Rspack
class RsbuildCorePlugin {
  apply(compiler: Compiler): void {
    compiler.__rsbuildTransformer = transformer;   // loaders resolve handlers via the compiler
    for (const { handler, environment } of resolveFns) {
      if (environment && !isEnvironmentMatch(environment, environment.name)) continue;
      compiler.hooks.compilation.tap(pluginName, (compilation, { normalModuleFactory }) => {
        normalModuleFactory.hooks.resolve.tapPromise(pluginName, async (resolveData) => handler({...}));
      });
    }
    compiler.hooks.thisCompilation.tap(pluginName, (compilation) => {
      compilation.hooks.childCompiler.tap(pluginName, (childCompiler) => {
        childCompiler.__rsbuildTransformer = transformer;   // child compilers inherit transformers
      });
      for (const { descriptor, handler, environment } of processAssetsFns) {
        if (descriptor.targets && !descriptor.targets.includes(target)) continue;   // target filter
        if ((descriptor.environments && !descriptor.environments.includes(environment.name)) ||
            (pluginEnvironment && !isEnvironmentMatch(pluginEnvironment, environment.name))) continue;
        compilation.hooks.processAssets.tapPromise(
          { name: pluginName, stage: mapProcessAssetsStage(descriptor.stage) }, ...);
      }
    });
  }
}
chain.plugin('RsbuildCorePlugin').use(RsbuildCorePlugin);
```
```ts
// expose/useExposed: environment key shadows global sentinel
const key = options?.environment ?? GLOBAL_EXPOSED_KEY;      // Symbol('global-exposed')
const createUseExposed = (currentEnvironment?) => (id) => {
  const exposedAPIs = exposed.get(id);
  if (!exposedAPIs) return undefined;
  if (currentEnvironment !== undefined && exposedAPIs.has(currentEnvironment))
    return exposedAPIs.get(currentEnvironment);
  return exposedAPIs.get(GLOBAL_EXPOSED_KEY);
};
```

**Flow:** every API factory is created once and parameterized per environment when a plugin's setup runs (`await setup(context.getPluginAPI!(environment))`). `api.transform(descriptor, handler)` mints an id, stores the handler in `transformer`, then taps `modifyBundlerChain` (env-tagged) to add a module rule whose loader is a generic `transformLoader.mjs` carrying `{id, getEnvironment}` — the loader looks up `compiler.__rsbuildTransformer[id]` at transform time and remaps source maps via `@jridgewell/remapping`. `api.processAssets` defers to the same core plugin so stage mapping ('additional'…'report' → Rspack PROCESS_ASSETS_STAGE_*) and target/env filtering happen at apply time. `onExit` lazily registers ONE process exitHook regardless of tap count. Config getters are phase-guarded: `getNormalizedConfig` throws until `modifyRsbuildConfig` has run.

**Invariant:** handlers must be filtered by BOTH the descriptor's targets/environments AND the registering plugin's environment; child compilations must inherit `__rsbuildTransformer` or worker/html-child transforms silently no-op. `undefined`-returning transform handlers mean "pass through unchanged".

**Probe:** `tests/environments.test.ts:420-462` pins exposure resolution exactly: `['global: global', 'web: web', 'node: global']` (env-scoped provider shadows global only in its own env). `tests/hooks.test.ts:38-70` pins single-fire onExit through process 'exit' event.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "initPluginAPI getTransformHook setProcessAssets setResolve createUseExposed", limit: 10 });
```

## Verdict
Adopt the collector-array + single bridge plugin + symbol-keyed handler map pattern for any loader-based tool exposing high-level plugin APIs. Adapt the loader path injection and source-map remap choice. Omit rsbuild's concrete descriptor fields beyond test/include/resourceQuery semantics shown. Coverage caveat: probes from on-disk specs; no runner this run.
