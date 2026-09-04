<!-- capsule-v2 -->
# FS module cache key — what belongs in the on-disk transform-cache key, and which inputs must never silently change it?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b3`); Codebase Memory `vitest`. **Question:** How is the sha1 cache key for the disk-backed module cache composed so a stale cache can never serve code transformed under different settings?

## Environment-hash + module-input key assembly
**Path/Symbol:** `packages/vitest/src/node/cache/fsModuleCache.ts:FileSystemModuleCache.generateCachePath` (:199–290), environment-hash block :231–268 (post-#11029), key concat :270–275; plugin opt-out `ignoresFsModuleCache` (:64–80).
**Signature:** `generateCachePath(vitestConfig: ResolvedConfig, environment: DevEnvironment, id: string, fileContent: string): string | null`.
**Data Shape:** Per-environment WeakMap `fsEnvironmentHashMap: WeakMap<DevEnvironment, string>` memoizes ONE precomputed digest = `sha1(NODE_ENV ?? '' + version + cacheConfig)`, where `cacheConfig = JSON.stringify({ root, base, mode, consumer, resolve, injectCjsGlobal, plugins: names-except-opted-out, configFileDependencies: file CONTENTS, environment.name, css })` with functions/RegExps stringified by the replacer. Module-dependent parts (`id`, raw `fileContent`) and `coverageAffectsCache` are appended per call; final `sha1(hashString)` names the file under a per-project cacheRoot.

### Decisive source
```ts
let environmentHash = this.fsEnvironmentHashMap.get(environment)
if (!environmentHash) {
  const cacheConfig = JSON.stringify({ root, base, mode, consumer, resolve,
    injectCjsGlobal, plugins: /* opted-out filtered */, configFileDependencies, environment, css }, replacer)
  // everything in the key that does not depend on the module, as one digest
  environmentHash = hash('sha1', (process.env.NODE_ENV ?? '') + this.version + cacheConfig, 'hex')
  this.fsEnvironmentHashMap.set(environment, environmentHash)
}
hashString += id
  + fileContent
  + environmentHash
  + coverageAffectsCache
```

**Flow:** bail out FIRST if source contains `import.meta.glob(` (depends on other files — cached path would be wrong); custom generators may veto caching (`return false`) or append key material → env hash computed once per DevEnvironment → per-module sha1 over id+content+envHash+coverage flag → path joined under `fsModuleCachePath || workspace-root node_modules/.vitest-cache`, mkdir'd lazily, memoized in `saveMemoryCache`.
**Invariant:** EVERYTHING that changes transform output must sit in the key: config-file dependency CONTENTS are hashed (not paths/mtime), plugin NAMES are keyed with an explicit per-plugin opt-out API (`api.vitest.ignoreFsModuleCache`, deprecated `experimental.` twin still honored with one deprecation warning per plugin). The #11029 form hashes NODE_ENV+version+config ONCE per environment — behavior-identical to concatenating them per-call, so porters may keep either shape but must not drop any input class. A porter who keys only on mtime serves stale transforms after config edits.
**Probe:** `grep -c 'environmentHash' packages/vitest/src/node/cache/fsModuleCache.ts` = 5 (:43/:231×2/:264/:272 post-#11029 sites); `grep -n "version = "` pins `'1.0.0-beta.6'` (:41 — bumped BY #11029 to invalidate all pre-existing caches); `grep -cF 'import.meta.glob(' …` = 1 (:207 sole bail-out). All verified on disk at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "generateCachePath fsCacheKeyGenerators ignoreFsModuleCache lockfileHash", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt content-keyed cache invalidation with an explicit plugin opt-out and the glob bail-out. Adapt the config-field list to whatever your host's transformer options actually are. Omit the WeakMap memoization if you recompute keys rarely — but keep every input class in the digest.
