<!-- capsule-v2 -->
# Context model — what is exposed on `context`, why is it Proxy-guarded, and where does the HMR token come from?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know the two-layer context (internal vs public) and why EnvironmentContext allows exactly one writable property.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/createContext.ts:getBrowserslistByEnvironment` (48–70), `updateEnvironmentContext` (93–138), `updateContextByNormalizedConfig` (140–144), `createPublicContext` (146–173), `createContext` (179–225); types in `packages/core/src/types/context.ts:InternalContext` (93–127), `BuildState` (78–90).
**Signature:** `createContext(options, userConfig, logger, loadConfigResult?): Promise<InternalContext>`.
**Data Shape:** Internal = public RsbuildContext (`version, rootPath, configFile, configFileDependencies, distPath, cachePath, devServer?, action?, callerName`) + internals `{logger, hooks, restartManager, config, originalConfig, normalizedConfig?, getPluginAPI?, environments, environmentList, specifiedEnvironments?, buildState, socketServer?, publicPathnames}`; EnvironmentContext = `{index, name, entry, htmlPaths, distPath, browserslist, tsconfigPath?, config, manifest?, webSocketToken}`.

### Decisive source
```ts
// dev-only auth token per environment: sha256 of root+name, hex-truncated to 16
const webSocketToken = context.action === 'dev' ? await hash(context.rootPath + name) : '';
// hash() = crypto sha256 hex slice(0,16) — see helpers/index.ts:229-238
```
```ts
// EnvironmentContext proxy: everything readonly EXCEPT 'manifest'
new Proxy(environmentContext, {
  set(target, prop, newValue) {
    if (prop === 'manifest') { target[prop] = newValue; }
    else { context.logger.error(`EnvironmentContext is readonly, you can not assign to the "environment.${prop}" prop.`); }
    return true;  // always true → assignment silently ignored outside strict mode
  },
});
```
```ts
// Public context allowlist proxy — internal keys resolve to undefined
return new Proxy(context, {
  get(target, prop) { if (exposedKeys.includes(prop)) return target[prop]; return undefined; },
  set(target, prop) { target.logger.error(`Context is readonly ... "context.${prop}"`); return true; },
});
```

**Flow:** `createContext` resolves rootPath (user `root` absolutized against cwd), merges defaults via `withDefaultConfig` (which also inherits `server.base` into both assetPrefixes, logLevel into client, enables lazyCompilation imports by default, auto-detects tsconfig), instantiates all hooks + restartManager wired to `onRestart.callBatch`, seeds buildState `{stats:null,status:'idle',hasErrors:false,time:{}}`. After normalization `updateEnvironmentContext` builds one proxied EnvironmentContext per env (browserslist resolved with jiti-proxy cloning for overrideBrowserslist — issue #8063 comment), registers them by index AND name, then `distPath` becomes the common parent across environments.

**Invariant:** plugins only ever see the allowlisted public context or the proxied environment contexts — a porter that hands out raw internal references breaks the write-protection contract; `webSocketToken` MUST be empty for non-dev actions or preview servers would accept socket upgrades.

**Probe:** `tests/environments.test.ts:6-35` pins normalized context shape/distPath inheritance. `helpers.test.ts:234-262` pins `getCommonParentPath` semantics incl. no-common-parent → `''`. Browserslist Proxy clone pinned by source comment at createContext.ts:54-58 (no direct unit test — coverage caveat recorded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "createPublicContext updateEnvironmentContext webSocketToken createEnvironmentAsyncHook context", limit: 10 });
```

## Verdict
Adopt two-layer context with allowlist proxies and derived-token-per-environment for any multi-env build tool. Adapt exposed key set and token derivation to host security model. Omit rsbuild's browserslist caching details beyond the memo-by-path+NODE_ENV note. Coverage caveat: token hashing has no dedicated unit test upstream (deterministic source read only).
