<!-- capsule-v2 -->
# Worker loader — how do `?worker` imports become URL wrappers, and why must inline workers be single-file?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `rsbuild`. **Question:** a porter implementing web-worker support from query-gated imports must reproduce the non-inline wrapper, the child-compiler inline build with its eager-dynamic-import invariant, and the blob→data-URL fallback ladder.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/worker.ts:pluginWorker` (5–22) — oneOf `JS_WORKER` gated by `WORKER_QUERY_REGEX = /[?&]worker(?:&|=|$)/` (constants.ts:76); `packages/core/src/loader/workerLoader.ts` — `getWorkerWrapper` (27–40), `getInlineWorkerWrapper` (45–84), `compileInlineWorker` (92–211), entry decision (213–232).
**Signature:** `workerLoader(): Promise<void>` — no resource input; options `{name?}`; branches on `INLINE_QUERY_REGEX /[?&]inline(?:&|=|$)/`.
**Data Shape:** non-inline → emits an ES-module default-export factory; inline → compiles worker source via a CHILD compilation and embeds it as a JSON-stringified string inside generated wrapper code.

### Decisive source
```ts
// non-inline: basename-only request — the emitted chunk sits next to the importer's output
const toWorkerRequest = (resourcePath: string) =>
  `./${normalizePath(path.basename(resourcePath))}`;
return `export default function WorkerWrapper(options) {
  return new Worker(new URL(${JSON.stringify(workerRequest)}, import.meta.url), ${workerOptions});
}`;   // workerOptions = { type: "module"?, name: options && options.name }
```
```ts
// inline: child compiler invariants (selections from compileInlineWorker)
childCompiler.options.module = { ...moduleOptions,
  parser: { ...parserOptions, javascript: {
    ...parserOptions.javascript, dynamicImportMode: 'eager',  // Blob/data URLs cannot load relative chunks
}}};
new rspack.LoaderTargetPlugin('webworker').apply(childCompiler);
new rspack.EntryPlugin(context.context ?? path.dirname(context.resourcePath),
  context.resourcePath, path.parse(context.resourcePath).name).apply(childCompiler);
// runAsChild → exactly ONE js asset allowed:
if (extraJsFiles.length > 0) reject(new Error(
  `[rsbuild:worker] Inline workers do not support code splitting yet. Use ?worker instead, …`));
deleteAsset(compilation, workerFilename); deleteAsset(compilation, `${workerFilename}.map`);
for (const file of childCompilation.fileDependencies) context.addDependency(file);   // + context/missing deps
```

**Flow:** plugin adds the query rule at `order: 'pre'` inside the JS rule → loader checks `inline`: absent → emit URL wrapper (module flag from `compilation.outputOptions.module` decides `type:"module"` and chunkFormat/chunkLoading overrides on the child compiler); present → child-compile to one JS file, strip `sourceMappingURL` lines, embed source into a blob-wrapper that prepends its own `URL.revokeObjectURL(import.meta.url)` INSIDE the blob (self-revoking), attaches an error-listener revoke, and falls back to `data:text/javascript;charset=utf-8,` + encodeURIComponent when Blob/URL APIs are missing.

**Invariant:** inline workers are single-file by construction — dynamic imports forced eager, code-splitting rejected loudly, and the child asset + `.map` deleted from the PARENT compilation so only the wrapper module ships. Wrapper code stays ES6-compatible because it bypasses user transforms.

**Probe:** e2e cases `e2e/cases/workers/worker-query-inline/` and `…/worker-query-inline-dynamic-import/` exercise exactly this path (retrieved rank#2–5 for "inline worker child compiler blob object url revoke"). Source pins executed: `dynamicImportMode: 'eager'` (workerLoader.ts:129), splitChunks.ts:270 uses the same eager mode — same invariant family. No unit suite exists for workerLoader.ts (caveat).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "inline worker child compiler blob object url revoke", limit: 10 });
```
Executed post-reindex: `compileInlineWorker` 92–211 and `getInlineWorkerWrapper` 45–84 resolve line-exact vs direct read.

## Verdict
Adopt the two-shape contract (URL wrapper vs embedded blob) and the child-compiler recipe (target override, eager imports, one-asset rejection, dep propagation, parent-side deletion). Adapt the chunk-loading overrides and module flags to your bundler's output options. Omit rsbuild's `webkitURL` compat shims only if you drop legacy Safari. Coverage caveat: behavior verified by e2e case inventory + byte-exact source reads; suites not executable in this lane (no node_modules).
