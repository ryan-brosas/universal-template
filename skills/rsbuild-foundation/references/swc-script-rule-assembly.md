<!-- capsule-v2 -->
# SWC script rule assembly — why do include conditions accumulate additively and env get deleted when jsc.target appears?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must keep the include/exclude accumulation order, polyfill alias wiring, and the jsc.target/env mutual-exclusion fix intact.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/swc.ts` — `applyScriptCondition` 21–51, `getDefaultSwcConfig` 53–91, plugin setup 96–195 (oneOf ladder 113–120, dataUriRule cloneDeep 183–191), core-js resolution 197–237, decorator switch 268–294.
**Signature:** `applyScriptCondition({rule,isDev,config,rsbuildTarget})`; `applyCoreJs(swcConfig, polyfillMode, rootPath): coreJsDir`.
**Data Shape:** swc loader options tree (jsc/env/transform); rule includes = Set-like additive list.

### Decisive source
```ts
rule.include.add({ not: NODE_MODULES_REGEX });            // app code first…
rule.include.add(/\.(?:ts|tsx|jsx|mts|cts)$/);            // …but TS/JSX ALWAYS compile
if (rsbuildTarget === 'web' && isDev)
  rule.include.add(/[\\/]@rsbuild[\\/]core[\\/]dist[\\/]/); // runtime itself down-leveled for legacy dev
```
```ts
// `jsc.target` and `env` cannot be set at the same time
if (mergedConfig.jsc?.target !== undefined && mergedConfig.env?.targets !== undefined &&
    Object.keys(mergedConfig.env).length === 1) delete mergedConfig.env;
...
dataUriRule...use(CHAIN_ID.USE.SWC).loader(builtinSwcLoaderName)
  .options(cloneDeep(mergedConfig));                      // data-URI branch MUST get its own copy
```
```ts
swcConfig.env!.coreJs = version;                          // major.minor from resolved core-js package.json, '3' fallback
if (polyfillMode === 'usage') swcConfig.env!.shippedProposals = true;
for (const item of [mainRule, dataUriRule]) item.resolve.alias.set('core-js', coreJsDir);
```

**Flow:** decorators map legacy→legacyDecorator+decoratorMetadata+`useDefineForClassFields:false` (#6571) vs 2022-03/2023-11→decoratorVersion; transformImport entries reduce function-form configs into an ARRAY push (never replace); polyfill mode copied verbatim into env.mode for web targets only; user tools.swc deepmerges OVER builtin defaults.
**Invariant:** (1) include is additive — replacing instead of adding breaks either node_modules exclusion or forced TS compilation; (2) deleting env ONLY when it holds nothing but targets preserves user-supplied env keys alongside jsc.target; (3) the second loader use() needs a CLONE because rspack chain options objects get frozen/mutated per rule.
**Probe:** unit `packages/core/tests/swc.test.ts:25/:33` (usage/entry preset-env modes), :49 ("correct core-js version"), :64/:76 (transformImport apply + undefined-return skip), :109 ("decorators version 2023-11").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginSwc applyScriptCondition getDefaultSwcConfig applyCoreJs decoratorMetadata", limit: 8 });
```

## Verdict
Adopt additive include semantics, forced-TS-compile carve-out, target/env exclusivity repair, cloned options for sibling rules, and version-sniffed core-js aliasing. Adapt decorator version keys and polyfill modes to your compiler. Omit builtin-swc specifics if using babel.
