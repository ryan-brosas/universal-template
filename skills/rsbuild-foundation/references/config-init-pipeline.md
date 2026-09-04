<!-- capsule-v2 -->
# Config init pipeline — what is the exact order from user config to normalized per-env configs to Rspack configs?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know the six ordered phases and their guard rails (memoization, plugin-mutation warning, deterministic sequential generation) or hook timing breaks.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/initConfigs.ts:modifyRsbuildConfig` (37–56), `initEnvironmentConfigs` (95–176), `validateRsbuildConfig` (178–216), `initRsbuildConfig` (227–297), `initConfigs` (299–349); plus `packages/core/src/rspackConfig.ts:generateRspackConfig` (171–198) and `configChain.ts:modifyBundlerChain` (4–26).
**Signature:** `initRsbuildConfig({context, pluginManager}): Promise<NormalizedConfig>`; `initConfigs(...): Promise<{rspackConfigs}>`.
**Data Shape:** `context.normalizedConfig` memoizes the whole result; per-env merge = `{...base, dev: pick(dev, allowedEnvironmentDevKeys), ...envConfig}` where allowed dev keys are exactly `[hmr, client, liveReload, browserLogs, writeToDisk, assetPrefix, progressBar, lazyCompilation]`.

### Decisive source
```ts
export async function initRsbuildConfig({ context, pluginManager }) {
  if (context.normalizedConfig) return context.normalizedConfig;      // 1. memo gate
  await initPlugins({ context, pluginManager });                      // 2. setup all plugins
  await modifyRsbuildConfig(context);                                 // 3. callChain + warn if plugins array changed
  const normalizedBaseConfig = normalizeConfig(context.config, context.rootPath);  // 4. defaults+mode
  const mergedEnvironments = initEnvironmentConfigs(normalizedBaseConfig, context.rootPath,
                                                   context.specifiedEnvironments);
  for (const [name, config] of Object.entries(mergedEnvironments)) {  // 5. per-env modify + dev re-merge
    const environmentConfig = await modifyEnvironmentConfig(context, config, name);
    environments[name] = { ...environmentConfig,
      dev: { ...normalizedBaseConfig.dev, ...environmentConfig.dev },
      server: normalizedBaseConfig.server };
    // tsconfigPath absolutized; collected when aliasStrategy==='prefer-tsconfig' → watchFiles restart entry
  }
  context.normalizedConfig = { ...normalizedBaseConfig, environments };
  await updateEnvironmentContext(context, environments);   // builds EnvironmentContext proxies + tokens
  updateContextByNormalizedConfig(context);                // distPath = common parent of env dists
  validateRsbuildConfig(context, context.normalizedConfig); // server.base slash check; target whitelist throw
  return context.normalizedConfig;
}
```
```ts
// initConfigs: SEQUENTIAL generation — comment pins intent
// Generate Rspack configs sequentially to ensure deterministic ordering and stable results
for (const [environmentName, config] of Object.entries(normalizedConfig.environments)) {
  rspackConfigs.push(await generateRspackConfig({ target: config.output.target, context, environmentName }));
}
```

**Flow:** each Rspack config is chain-first (`modifyBundlerChain` runs every tap against a fresh RspackChain, then user `tools.bundlerChain` callbacks), converted with `chain.toConfig()`, then `tools.rspack` reduce-configs with live-reference updates via the mergeFn callback, then validated (`devServer` key warned; an Rsbuild-shaped plugin inside rspack plugins throws). Node-target defaults applied in `applyEnvironmentDefaultConfig`: empty js distPath, `output.module = isServer`, `minify = !isServer`. Missing-environment after filtering by `specifiedEnvironments` throws a dedicated error.

**Invariant:** phase order plugins→modifyRsbuildConfig→normalize is not negotiable — normalized config getters throw before step 3 completes and plugin mutation after step 2 only warns ("Cannot change plugins via modifyRsbuildConfig"); env configs must re-merge base `dev` AFTER modification because base dev keys are stripped from env scope except the allowlist.

**Probe:** `tests/environments.test.ts:6-35` normalize-context snapshot; `:100-155` single-env modify; `:198-232` specified-environment filtering (`environment:['ssr']` runs only ssr + global plugins); `tests/pluginApply.test.ts:65-100` memoized init returning fresh objects. `e2e/cases/plugin-api/plugin-hooks/index.test.ts:6-33` fixes ModifyRsbuildConfig BEFORE ModifyEnvironmentConfig BEFORE chain/config hooks.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "initRsbuildConfig initEnvironmentConfigs generateRspackConfig validateRsbuildConfig", limit: 10 });
```

## Verdict
Adopt the six-phase pipeline, dev-key allowlist for environment scoping, and sequential deterministic config generation. Adapt the allowlist contents and validation rules to host options. Omit rsbuild's inspect/debug file emission unless building an inspector (see `inspectConfig.ts` separately). Coverage caveat: probes from on-disk specs.
