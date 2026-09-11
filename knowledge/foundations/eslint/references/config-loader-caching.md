<!-- capsule-v2 -->
# Config loader caching — how is one config file found per directory and its config array cached across thousands of files?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you cache config-file resolution so a lint run touches each config file exactly once?

## ConfigLoader promise-map caching
**Path/Symbol:** `lib/config/config-loader.js:ConfigLoader` (:286–501+; decisive: `#locateConfigFileToUse` :324–345, `#calculateConfigArray` :353–374, `getCachedConfigArrayForPath` :471–501).
**Signature:** `findConfigFileForPath(fileOrDirPath)`, `loadConfigArrayForFile(filePath)`, `getCachedConfigArrayForFile(filePath)` (sync).
**Data Shape:** two private maps — `#configFilePaths: Map<absDir, {configFilePath, basePath}|Promise<...>>` and `#configArrays: Map<configFilePath, FlatConfigArray|Promise<FlatConfigArray>>`. Both are seeded with the *Promise* and replaced with the unwrapped value.

### Decisive source
```js
async #locateConfigFileToUse(fromDirectory) {
  if (this.#configFilePaths.has(fromDirectory)) return this.#configFilePaths.get(fromDirectory);
  const resultPromise = ConfigLoader.locateConfigFileToUse({ useConfigFile: this.#options.configFile, cwd, fromDirectory });
  // ensure `ConfigLoader.locateConfigFileToUse` is called only once for `fromDirectory`
  this.#configFilePaths.set(fromDirectory, resultPromise);   // store the PROMISE first (dedupe concurrent callers)
  const result = await resultPromise;
  this.#configFilePaths.set(fromDirectory, result);          // unwrap for the sync getter
  return result;
}
// sync getter throws rather than await:
if (typeof configFilePathInfo.then === "function") throw new Error(`Config file path for ${fileOrDirPath} has not yet been calculated...`);
```

**Flow:** file → resolve dirname → locate config file upward (cached per dir) → assert a config exists → load + normalize its array (cached per config path) → later files hit `getCachedConfigArrayForFile` which resolves synchronously with zero I/O.
**Invariant:** storing the promise *before* awaiting is what deduplicates N concurrent file lookups into one search — caching only resolved values would still run N parallel find-ups. The sync getter deliberately throws on pending entries instead of blocking, keeping hot paths synchronous. Config modules reload via an `?mtime=<ms>` import query plus targeted `require.cache` eviction when mtime changes (never time-based queries — unbounded import-cache growth).
**Probe:** `tests/lib/config/config-loader.js` (cache hits, pending-promise errors, mtime reload).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "ConfigLoader getCachedConfigArrayForFile loadConfigFile mtime", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.config.config-loader.ConfigLoader" });
```

## Verdict
Adopt the promise-first two-level cache and the sync-throw-on-pending contract; adapt the upward filename list (`eslint.config.{js,mjs,cjs,ts,...}`) and jiti/native-TS branches to host; omit the warning-service plumbing.
