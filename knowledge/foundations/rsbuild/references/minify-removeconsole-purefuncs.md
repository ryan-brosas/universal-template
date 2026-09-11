<!-- capsule-v2 -->
# Minify option parsing + removeConsole via pure_funcs — why does drop-console use compress.pure_funcs and never delete calls?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must map `performance.removeConsole` onto SWC without breaking the minify-gate ladder or the CSS-minifier option inheritance.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/minimize.ts` — CONSOLE_METHODS 10–33, `getSwcMinimizerOptions` 40–86, `parseMinifyOptions` 88–111, plugin registration 113–199 (array-indexed minimizers 124–143 / 173–195), css defaultOptions 153–171.
**Signature:** `parseMinifyOptions(config): {minifyJs, minifyCss, jsOptions?, cssOptions?}`; `getSwcMinimizerOptions(config, jsOptions?)`.
**Data Shape:** `minify: boolean | {js?, css?, jsOptions?, cssOptions?}` where each sub-flag may be `'always'`; options arrays register MULTIPLE minimizers (`CHAIN_ID.MINIMIZER.JS`, `JS-1`, …).

### Decisive source
```ts
if (removeConsole === true)       options.minimizerOptions.compress = { pure_funcs: ALL_CONSOLE_PURE_FUNCS };
else if (Array.isArray(removeConsole)) options.minimizerOptions.compress = { pure_funcs: removeConsole.map(m => `console.${m}`) };
...
options.minimizerOptions.format.asciiOnly = config.output.charset === 'ascii';
if (jsOptions) return deepmerge(options, jsOptions);   // USER options win AFTER builtin mapping
```
```ts
// parseMinifyOptions gates:
minifyJs:  minify.js  !== false && (minify.js  === 'always' || isProd),
minifyCss: minify.css !== false && (minify.css === 'always' || isProd),
// css minimizer inherits LOADER options so dev/prod CSS stays consistent:
minimizerOptions: { targets: isPlainObject(loaderOptions.targets) ? environment.browserslist : loaderOptions.targets,
                    ...pick(loaderOptions, ['drafts','include','exclude','nonStandard','pseudoClasses','unusedSymbols','errorRecovery']) }
```

**Flow:** `output.minify` defaults true but EVERYTHING still requires `mode==='production'` unless a sub-flag says `'always'`; false disables that channel permanently. removeConsole marks console methods PURE instead of dropping AST nodes — safe under dead-code elimination, keeps semantics if expression result is used. legalComments maps inline→format.comments='some'+extractComments:false / linked→extractComments:true / none→comments:false.
**Invariant:** (1) pure_funcs entries MUST be fully-qualified `console.<method>` strings; (2) deepmerge direction is {builtin} ← {user} (user last); (3) an EMPTY options array still registers one default minimizer (139–140, 191–192) — zero minimizers is not a valid state.
**Probe:** unit `packages/core/tests/minimize.test.ts:217` ("should dropConsole when performance.removeConsole is true"), :233 (specific-methods array); snapshot pins plugin registration.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginMinimize parseMinifyOptions getSwcMinimizerOptions pure_funcs", limit: 8 });
```

## Verdict
Adopt the tri-state minify ladder ('always' escape hatch), pure_funcs console removal, loader→minimizer option inheritance, and array-multiplied minimizer ids. Adapt method list to your runtime's console surface. Omit swc-specific format fields if using terser/esbuild.
