<!-- capsule-v2 -->
# Instance assembly — how does `createRsbuild` build one instance whose actions share a lazily-created compiler, with the action type frozen on first use?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know when the config is resolved relative to plugin registration, and why calling two different actions throws instead of silently rebuilding.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/createRsbuild.ts:createRsbuild` (160–441), helpers `applyEnvsToConfig` (106–145), `isLoadConfigResult` (147–155), `initAction` (310–314), `getFlattenedPlugins` (405–412).
**Signature:** `async function createRsbuild(options?: CreateRsbuildOptions): Promise<RsbuildInstance>`.
**Data Shape:** options `{cwd?, callerName?, environment?, config?|rsbuildConfig? (object | LoadConfigResult | async factory), loadEnv?: boolean|LoadEnvOptions, restart?}` → instance with `logger`, action methods (`build`, `preview`, `startDevServer`, `createDevServer`, `createCompiler`, `inspectConfig`, `initConfigs`) plus picked PluginManager methods and global plugin API.

### Decisive source
```ts
const createCompiler = (async () => {
  initAction();
  const result = await baseCreateCompiler({ context, pluginManager, rsbuildOptions: resolvedOptions });
  return result.compiler;
}) as CreateCompiler;
```
```ts
const initAction = (mode: string | undefined = config.mode) => {
  if (!context.action) {
    context.action = mode === 'development' ? 'dev' : 'build';
  }
};
```
```ts
// initConfigs guard (same file, 340–361)
if (context.action && options?.action && context.action !== options.action) {
  throw new Error(`[rsbuild] initConfigs() can only be called with the same action type.
  - Expected: ${context.action}
  - Actual: ${options?.action}`);
}
```

**Flow:** (1) optionally `loadEnv()` up-front; (2) resolve config — factory awaited, `LoadConfigResult` unwrapped via duck-typed `isLoadConfigResult`; (3) logger: `config.customLogger ?? createLogger({...defaultLogger.options, level})` so instances are isolated; apply `config.logLevel` unless debug; (4) `applyEnvsToConfig`: public vars spread UNDER user `source.define` (user wins), env file paths appended to `dev.watchFiles` as `type:'restart'`, and pushed into `performance.buildCache.buildDependencies` for cache invalidation; (5) create PluginManager + context + per-env plugin API; register 32 default plugins; (6) each action method sets `context.action` then defaults NODE_ENV (`build/preview→production`, `dev→development`) only when unset, calls `initRsbuildConfig` lazily; (7) after instance creation, user `config.plugins` are flattened by `getFlattenedPlugins` — a do/while loop awaiting promises until none remain, flattening infinitely deep nested arrays — then added; environment plugins added with `{environment: name}` and skipped when not in `specifiedEnvironments`.

**Invariant:** the compiler is created at most once per instance (every action awaits the same closure); once `context.action` is set it never changes on that instance — mixing `initConfigs({action})` types is a thrown error, not silent re-init. Env cleanup hooks are registered on BOTH `onCloseBuild` and `onCloseDevServer` so either exit path unmounts process.env keys.

**Probe:** `tests/pluginApply.test.ts:65-100` ("should not return the same config when called multiple times") pins that repeated `initConfigs` runs setup exactly once yet returns fresh config objects; `tests/pluginApply.test.ts:102-121` pins the mixed-action throw message verbatim.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "createRsbuild initAction applyEnvsToConfig getFlattenedPlugins", limit: 10 });
```

## Verdict
Adopt single-lazy-compiler + frozen-action + promise-flattened plugin registration as the reusable harness contract. Adapt the specific default-plugin list (host product surface) and NODE_ENV side effects. Omit rsbuild's exact error strings unless reproducing UX. Coverage caveat: deterministic source/test probes only in this run (no runner); all cited paths `metadata_match`.
