<!-- capsule-v2 -->
# importLoaders dual counter — why do inline/url branches count one more preceding loader than main?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must not flatten `importLoaders` to a single number — the inline/?url branches deliberately see a different count than the main branch.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/css.ts` — counter init 324–327, increments 349–357 & 400–407, consumption 430–442.
**Signature:** local `importLoaders = { normal: 0, inline: 0 }` mutated during chain assembly.
**Data Shape:** two integer counters; `finalOptions.importLoaders` = `normal` for MAIN, `inline` for INLINE/URL types.

### Decisive source
```ts
const importLoaders = { normal: 0, inline: 0 };
...
if (config.tools.lightningcssLoader !== false) {
  if (emitCss) { importLoaders.normal++; }   // extract/style path counts it for main
  importLoaders.inline++;                    // inline styles bypass Rspack minimizers
  ...
}
...
if (postcss enabled) {
  if (emitCss) { importLoaders.normal++; }
  importLoaders.inline++;
  ...
}
await updateRules((rule, type) => {
  const finalOptions = type === 'inline' || type === 'url'
    ? { ...cssLoaderOptions, exportType: 'string', modules: false, importLoaders: importLoaders.inline }
    : { ...cssLoaderOptions, importLoaders: importLoaders.normal };
```

**Flow:** every pre-css-loader added only to inline/url paths (lightningcss when skipped on main via `{skipMain:!emitCss}`, postcss likewise) bumps ONLY `inline`; loaders that also land on main bump BOTH (normal only when emitCss because when emit=false main has no style pipeline at all). Final css-loader options select the counter by branch type.
**Invariant:** css-loader's `@import` resolution must know exactly how many loaders precede it ON ITS OWN BRANCH; sharing one number across branches mis-resolves `@import` in either extracted or inline CSS. `modules:false + exportType:'string'` on inline/url is what makes `?inline` return a string even for a `.module.css` file path matched by URL_QUERY.
**Probe:** e2e `e2e/cases/css/import-loaders/index.test.ts:4` ("should compile CSS Modules which depends on importLoaders correctly"); `css/postcss-add-plugins/index.test.ts:4` pins addPlugins ordering through this plane.
**Coverage caveat:** unit coverage absent upstream (chain assembly asserted via e2e output).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginCss modifyBundlerChain importLoaders updateRules", limit: 8 });
```

## Verdict
Adopt the twin-counter pattern for any multi-branch loader chain whose branches host different loader stacks. Adapt counter keys to your branch names. Omit lightningcss-specific skip conditions unless porting the whole CSS plane.
