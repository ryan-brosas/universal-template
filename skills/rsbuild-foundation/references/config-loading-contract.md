<!-- capsule-v2 -->
# loadConfig + defineConfig contract — why does the config function receive {env, command, envMode, meta} and get _privateMeta stamped?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the file-name ladder precedence, function-form config invocation params, and restart-relevant metadata stamping.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/loadConfig.ts` — ConfigParams 12–17, defineConfig overload 54–67 (const-generic typelevel return), DEFAULT_CONFIG_FILE_NAMES 70–77 (ts→js→mts→mjs→cts→cjs), `loadConfig` 79–128 (fresh:true 104, object validation 112–118, _privateMeta 120–123).
**Signature:** `loadConfig<Config>({cwd?, path?, configFileNames?, envMode?, meta?, loader?, command?, exportName?}): Promise<LoadConfigResult<Config>>`.
**Data Shape:** result {content, filePath, dependencies}; content = object | fn(params) | async fn.

### Decisive source
```ts
const configParams: ConfigParams = {
  env: nodeEnv,
  command: command ?? process.argv[2],   // 'dev' | 'build' | ... straight from CLI position
  envMode: envMode || nodeEnv,
  meta,
};
const result = await baseImpl<Config,[ConfigParams]>({ cwd, path, configFileNames, loader, exportName,
                                                      configParams: [configParams], fresh: true });
if (!isObject(result.content)) throw new Error(`The config must be an object or a function that returns an object, get ${...}`);
(result.content as RsbuildConfig)._privateMeta = { configFilePath: result.filePath, configFileDependencies: result.dependencies };
```

**Flow:** `fresh:true` bypasses require cache so watch-mode restarts see edited configs. dependencies (config file's own imports) feed pluginCache.buildDependencies.rsbuildConfig and the restart watcher. The type-level defineConfig distinguishes sync/async function forms purely for IDE typing — runtime returns the definition untouched.
**Invariant:** (1) the file ladder order matters — .ts must win over .js or stale compiled artifacts shadow source; (2) _privateMeta is INTERNAL: normalization reads it for restart/cache but user-visible config objects must not leak it into merge semantics; (3) non-object content throws LOUDLY before any bundler work.
**Probe:** e2e `cases/config/*` custom-config suites; unit coverage absent at unit layer (coverage caveat: integration-level pinning).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "loadConfig defineConfig ConfigParams DEFAULT_CONFIG_FILE_NAMES", limit: 8 });
```

## Verdict
Adopt param-injected config functions with fresh loading and metadata side-channel. Adapt file ladder to host naming. Omit @rstackjs/load-config internals.
