<!-- capsule-v2 -->
# buildDependencies cache invalidation set — why must framework/tsconfig/tailwind configs be listed explicitly?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the persistent-cache gating: which files invalidate, how the version key is built, and when caching silently stays off.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/cache.ts` — `getCacheDirectory` 11–16, `getBuildDependencies` 22–62, plugin 64–113 (cacheVersion digest 89–94, chain.cache 96–104).
**Signature:** `getBuildDependencies(context, environmentContext, additionalDependencies?): Promise<Record<string,string[]>>`.
**Data Shape:** buildCache: false | true | {cacheDirectory?, cacheDigest?: string[], buildDependencies?: string[]}; version = `${envName}-${env}` (+ `-<hash(digest)>`).

### Decisive source
```ts
// Rspack can't detect the changes of framework config, tsconfig, tailwind config and browserslist config.
// but they will affect the compilation result, so they need to be added to buildDependencies.
if (await isFileExists(rootPackageJson)) buildDependencies.packageJson = [rootPackageJson];
if (tsconfigPath) buildDependencies.tsconfig = [tsconfigPath];
if (context.configFile) buildDependencies.rsbuildConfig = [context.configFile, ...context.configFileDependencies];
if (await isFileExists(browserslistConfig)) buildDependencies.browserslistrc = [browserslistrc];
const tailwindConfig = findExists(['ts','js','cjs','mjs'].map((ext) => join(rootPath, `tailwind.config.${ext}`)));
```
```ts
const useDigest = Array.isArray(cacheConfig.cacheDigest) && cacheConfig.cacheDigest.length;
const cacheVersion = useDigest ? `${environment.name}-${env}-${await hash(JSON.stringify(cacheConfig.cacheDigest))}` : `${environment.name}-${env}`;
chain.cache({ type: 'persistent', version: cacheVersion,
              storage: { type: 'filesystem', directory: cacheDirectory },
              buildDependencies: Object.values(buildDependencies).flat() });
```

**Flow:** performance.buildCache=false (default) leaves rspack memory-cache defaults untouched — enabling flips to persistent filesystem storage under context.cachePath/rspack unless overridden. Digest entries let callers inject env-dependent salts (deploy vars, feature flags) that no file watch can see. Relative cacheDirectory resolves against project root.
**Invariant:** (1) every config file that influences output but isn't a module MUST be in buildDependencies or stale caches serve wrong builds; (2) environment NAME belongs in the version or web/node builds cross-pollinate; (3) missing files are skipped silently (isFileExists guards) — absence is normal, not error.
**Probe:** unit snapshot `packages/core/tests/cache.test.ts` (cases: default add / tsconfig watch / custom directory / cacheDigest table).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginCache getBuildDependencies getCacheDirectory buildCache", limit: 8 });
```

## Verdict
Adopt explicit non-module dependency listing + env-named versioned persistent storage with optional digest salt. Adapt watched-config list to host framework. Omit rspack storage specifics if using webpack's file-cache.
