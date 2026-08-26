<!-- capsule-v2 -->
# Node-addons transform — how are `.node` binaries shipped and re-required at runtime without bundler interference?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `rsbuild`. **Question:** a porter must know why `.node` files ride the raw transform surface (not an asset rule), how the emitted binary is named, and which require-form each output module format needs.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/nodeAddons.ts` — `getFilename` (5–8), `pluginNodeAddons` (10–65); rides `api.transform({ test: /\.node$/, targets: ['node'], raw: true })`.
**Signature:** `getFilename(resourcePath: string): string | null` → `path.parse(resourcePath).name + '.node'`; transform handler returns generated module source.
**Data Shape:** raw Buffer code in; emits `{basename}.node` via `emitFile`; returns CJS or ESM loader-module text with a `try/catch` whose error wraps `cause`.

### Decisive source
```ts
const getFilename = (resourcePath: string) => {
  const name = resourcePath && path.parse(resourcePath).name;
  return name ? `${name}.node` : null;
};
// …
emitFile(filename, code);
if (environment.config.output.module) {
  // ESM output — rebuild a require() from import.meta.url
  return `
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const require = createRequire(import.meta.url);
let native;
try { native = require(path.join(__dirname, "${filename}")); }
catch (error) { throw new Error('Failed to load Node.js addon: "${filename}"', { cause: error }); }
export default native;
`;
}
// CJS output — bypass the bundler's require entirely
return `
try {
  const path = __non_webpack_require__("node:path");
  module.exports = __non_webpack_require__(path.join(__dirname, "${filename}"));
} catch (error) { … same cause-wrapping throw … }
`;
```

**Flow:** node-target-only descriptor → raw Buffer → filename from basename → emit next to the consuming chunk → generate a thin re-exporter that loads the native file at RUNTIME (never parsed/bundled), branching on `output.module`: ESM synthesizes `createRequire(import.meta.url)`; CJS uses `__non_webpack_require__` so Rspack does not intercept the require.

**Invariant:** the addon bytes must reach disk untouched (`raw: true`) and be loaded by Node's true require at runtime; failures surface as a loud addon-load Error preserving the underlying cause. Web/web-worker targets get NO rule at all (target-scoped, not content-sniffed).

**Probe:** `packages/core/tests/nodeAddons.test.ts:19–45` pins rule ABSENCE for target `web` and `web-worker` (`matchRules(config,'a.node') === []`), :5–17 + snapshot pins presence/shape for `node` (loader `transformRawLoader.mjs`, options `{id:'rsbuild-transform-0', getEnvironment}`). Source pins executed: `__non_webpack_require__` at nodeAddons.ts:56–57.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginNodeAddons node addon raw transform emitFile non_webpack_require", limit: 10 });
```
Executed pre-reindex: `pluginNodeAddons` 10–65 served line-exact vs direct read.

## Verdict
Adopt target-gated raw-transform emission + runtime-require synthesis with cause-preserving errors. Adapt the emitted paths (`__dirname` join) to your dist layout and the bundler-bypass token if your host isn't webpack-lineage. Omit nothing behavioral — the file is fully capsuled here. Coverage caveat: suites not executable in this lane (no node_modules); snapshot text verified byte-for-byte on disk.
