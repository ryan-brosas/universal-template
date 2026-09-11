<!-- capsule-v2 -->
# HTML plugin implementation singleton — how does one selector choose native vs vendored-JS html-plugin, and why does the require go through a compiled folder?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `rsbuild`. **Question:** a porter supporting two implementations of a heavy bundler plugin must know the memoization boundary, the config key that flips between them, and the CommonJS-vendoring contract.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/pluginHelper.ts:getHTMLPlugin` (11–22); `packages/core/src/helpers/vendors.ts:requireCompiledPackage` (17–19) + CJS require shim (8); constants `COMPILED_PATH` (constants.ts:24 = `join(dirname, '../compiled')`).
**Signature:** `getHTMLPlugin(config?: NormalizedEnvironmentConfig): typeof HtmlRspackPlugin`; `requireCompiledPackage<T extends keyof CompiledPackages>(name: T)`.
**Data Shape:** module-global `htmlPlugin` memo; branch on `config?.html.implementation === 'native'` → `rspack.HtmlRspackPlugin` (type-asserted); otherwise lazily require `compiled/html-rspack-plugin/index.js`.

### Decisive source
```ts
let htmlPlugin: typeof HtmlRspackPlugin;

export function getHTMLPlugin(config?: NormalizedEnvironmentConfig) {
  if (config?.html.implementation === 'native') {
    return rspack.HtmlRspackPlugin as unknown as typeof HtmlRspackPlugin;   // no memo — direct binding
  }
  if (!htmlPlugin) {
    htmlPlugin = requireCompiledPackage('html-rspack-plugin');             // memoize ONLY the JS impl
  }
  return htmlPlugin;
}
```
```ts
// vendors.ts — vendored deps are CommonJS, so import.meta URL require:
export const require: NodeJS.Require = createRequire(import.meta.url);
export const requireCompiledPackage = <T extends keyof CompiledPackages>(name: T) =>
  require(`${COMPILED_PATH}/${name}/index.js`) as CompiledPackages[T];
```

**Flow:** every consumer that needs the HTML plugin calls this selector instead of importing either implementation. Native mode short-circuits to Rspack's built-in class each call; JS mode requires the prebundled CommonJS build from `packages/core/compiled/<name>/index.js` exactly once per process and caches it in module scope.

**Invariant:** the memo is keyed by NOTHING but success — first non-native call fixes the implementation for the process; typed registry (`CompiledPackages`) keeps vendored names exhaustive at compile time; ESM packages must bridge to CJS via `createRequire(import.meta.url)` because the compiled artifacts are CommonJS.

**Probe:** executed source pins: `implementation === 'native'` pluginHelper.ts:14; `createRequire(import.meta.url)` vendors.ts:8; `COMPILED_PATH` join constants.ts:24 with package.json `files: ["…","compiled",…]` proving the folder ships. No dedicated unit suite for either file at pin (grep over tests executed — zero matches); behavior of the selected plugin is covered indirectly by html.test.ts/e2e html suites.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "getHTMLPlugin html-rspack-plugin requireCompiledPackage compiled", limit: 10 });
```
Executed post-reindex: resolves `getHTMLPlugin` in pluginHelper.ts and `requireCompiledPackage` in helpers/vendors.ts at pin spans matching direct reads.

## Verdict
Adopt the two-implementation selector with implementation-scoped memoization and the typed vendored-dep require shim. Adapt the vendored-folder location and the flip-key naming to your product. Omit rsbuild's TODO type assertion once your host types align. Coverage caveat: no dedicated unit tests for these 22+19-line files; pinned by byte-exact source reads.
