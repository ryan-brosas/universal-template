<!-- capsule-v2 -->
# WASM rule — why does the `.wasm` rule scope to `new URL` dependencies, and what does `webassemblyModuleFilename` own?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `rsbuild`. **Question:** a porter wiring WebAssembly support must know which `.wasm` imports this rule may claim and which are left to Rspack's native WebAssembly support.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/wasm.ts:pluginWasm` (5–31) — whole plugin; filename from shared `getFilename(config, 'wasm', isProd)` helper.
**Signature:** `modifyBundlerChain((chain, { CHAIN_ID, environment, isProd }))` → output tweak + one module rule.
**Data Shape:** filename = `posix.join(config.output.distPath.wasm, getFilename(…))`; snapshots pin the default as `static/wasm/[contenthash:10].module.wasm`.

### Decisive source
```ts
chain.output.webassemblyModuleFilename(filename);

// support new URL('./abc.wasm', import.meta.url)
chain.module
  .rule(CHAIN_ID.RULE.WASM)
  .test(/\.wasm$/)
  // only include assets that came from new URL calls
  .dependency('url')
  .type('asset/resource')
  .set('generator', { filename });
```

**Flow:** two independent mechanisms in one plugin: (1) `output.webassemblyModuleFilename` governs modules compiled through Rspack's native async/sync WebAssembly paths (`static/wasm/[contenthash].module.wasm`); (2) the RULE handles only url-dependency wasm — `dependency('url')` restricts matching to modules introduced by `new URL(..., import.meta.url)` so they emit as ordinary assets with the same filename template, instead of colliding with Rspack's intrinsic wasm pipeline.

**Invariant:** never let the asset rule swallow intrinsic WebAssembly imports — the `.dependency('url')` scoping IS the contract. Both surfaces must agree on the dist path so hashes/URLs line up regardless of import style.

**Probe:** `packages/core/tests/wasm.test.ts:5–19` builds a config with `distPath.wasm: 'static/wasm'` and snapshots `matchRules(config, 'a.wasm')`. Snapshot corroboration across suites: `"webassemblyModuleFilename": "static/wasm/[contenthash:10].module.wasm"` appears in default/output/environments/builder snapshot files (grep-executed). Source pins executed: `.dependency('url')` at wasm.ts:24.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginWasm webassemblyModuleFilename dependency url asset resource", limit: 10 });
```
Executed pre-reindex: `pluginWasm` 5–28 served line-exact vs direct read (plugin tail :29–30 closes setup).

## Verdict
Adopt the dual-mechanism split and the url-dependency scoping trick — it is the portable answer to "asset-ify WASM without breaking ESM wasm imports". Adapt filename templates and dist-path defaults to your conventions. Omit rsbuild's CHAIN_ID constant indirection. Coverage caveat: unit suite exists but was not executable in this lane (no node_modules); rule text verified byte-for-byte at pin.
