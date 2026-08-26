<!-- capsule-v2 -->
# ignoreCssLoader pitch gate — why does the non-emitting SSR build keep css-loader ONLY for CSS Modules?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce emitCss=false handling where global CSS dies at the pitch but module exports survive for SSR.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/loader/ignoreCssLoader.ts` whole 1–33; wiring `plugins/css.ts` 317–321 (use when !emitCss) and 444–449 (modules option forwarded).
**Signature:** `export const pitch: PitchLoaderDefinitionFunction<IgnoreCssLoaderOptions>(): string | undefined`.
**Data Shape:** options `{modules: CSSLoaderOptions['modules']}` — same normalized modules config css-loader will see.

### Decisive source
```ts
const ignoreCssLoader = function (source) {
  // if the source code includes '___CSS_LOADER_EXPORT___' it is NOT a CSS Modules file
  // (exportOnlyLocals is enabled), so we don't need to preserve it.
  if (source.includes('___CSS_LOADER_EXPORT___')) return '';
  return source;   // Preserve CSS Modules export for SSR.
};
// In non-emitting builds, skip css-loader and following CSS transforms for global CSS.
export const pitch = function () {
  const { modules } = this.getOptions();
  if (isCSSModules(modules, this)) return;   // undefined → continue chain (css-loader runs)
  return '';                                  // '' → skip ALL remaining loaders AND the module body
};
```

**Flow:** when output.emitCss is false (non-web targets by default), main branch installs ignoreCssLoader BEFORE css-loader. Pitch returns '' for global styles → no style side effects in server bundles. For CSS Modules the pitch falls through so css-loader runs with exportOnlyLocals:true (normalizeCssLoaderOptions) producing a JS module of class-name mappings that the SSR bundle imports. The normal phase then strips any residual loader-export sentinel.
**Invariant:** (1) order matters — ignore must sit BEFORE css-loader to be able to skip it; (2) pitch '' vs undefined are different outcomes (skip-everything vs continue-chain); (3) the sentinel check must run in the NORMAL phase because only css-loader's output contains it.
**Probe:** unit snapshot via `css.test.ts` (emitCss:false rule assembly); e2e `cases/css/emit-css` family + ssr cases pin observable behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "ignoreCssLoader pluginCss emitCss exportOnlyLocals", limit: 8 });
```

## Verdict
Adopt pitch-gated loader skipping with module-export preservation. Adapt sentinel string to your css-loader version. Omit style-loader/mini-css branches (covered by import-loaders capsule).
