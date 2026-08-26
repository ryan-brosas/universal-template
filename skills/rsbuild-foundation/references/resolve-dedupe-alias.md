<!-- capsule-v2 -->
# resolve alias + dedupe ladder — why does dedupe walk up node_modules and alias only absolutizes dotted relatives?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the dedupe→alias precedence, pnpm-safe package-dir walk, extensionAlias TS carve-out, and mjs fullySpecified fix.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/resolve.ts` — `applyAlias` 8–96 (dedupe skip-if-aliased 24–35, package.json-first resolution 37–46, node_modules walk-up 50–70, relative-absolutization 82–95), plugin 98–152 (extensionAlias 117–124, MJS rule 136–139, prefer-tsconfig 143–149).
**Signature:** `applyAlias({chain, config, rootPath, logger})`.
**Data Shape:** mergedAlias Record<name,string|string[]>; values may be package names (untouched) or paths.

### Decisive source
```ts
if (!pkgPath) {
  pkgPath = require.resolve(pkgName, { paths: [rootPath] });
  // Ensure the package path is `node_modules/@scope/package-name`
  const trailing = ['node_modules', ...pkgName.split('/')].join(sep);
  while (!pkgPath.endsWith(trailing) && pkgPath.includes('node_modules')) pkgPath = dirname(pkgPath);
}
```
```ts
const formattedValues = values.map((v) => typeof v === 'string' && v.startsWith('.') ? ensureAbsolutePath(rootPath, v) : v);
// TypeScript allows importing TS files with `.js` extension:
chain.resolve.extensionAlias.set('.js', ['.js','.ts','.tsx']).set('.jsx', ['.jsx','.tsx']);
// compatible with legacy packages with type="module" (webpack#11467):
chain.module.rule(CHAIN_ID.RULE.MJS).test(/\\.m?js/).resolve.set('fullySpecified', false);
```

**Flow:** dedupe resolves each listed package from the PROJECT root (not rsbuild's own tree), tries `<pkg>/package.json` first then falls back to main entry and walks UP directories until the path ends with node_modules/<pkg segments> — required under pnpm's symlinked store layout. Aliases already defined by the user win over dedupe for the same key (skip + debug log). Alias values are absolutized ONLY when starting with '.'; bare names pass through.
**Invariant:** (1) the dirname loop needs BOTH conditions or it walks past the real package into the store root; (2) extensionAlias must apply only to tsconfig projects (`!endsWith('jsconfig.json')`) or JS projects get phantom TS resolution; (3) fullySpecified:false must be set on its own rule BEFORE the js rule ordering concern noted in-source (#11467 modern.js failures).
**Probe:** unit `packages/core/tests/resolve.test.ts` (5 cases incl. alias/dedupe table); snapshot coverage via config.test.ts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginResolve applyAlias ensureAbsolutePath extensionAlias fullySpecified", limit: 8 });
```

## Verdict
Adopt root-relative dedupe with walk-up normalization and minimal-touch alias formatting. Adapt extensionAlias map to host compiler. Omit prefer-tsconfig branch if host lacks tsconfig-paths plugin.
