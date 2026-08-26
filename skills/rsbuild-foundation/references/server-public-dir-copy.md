<!-- capsule-v2 -->
# server plugin publicDir copy — why does copyOnBuild 'auto' skip node targets and dedupeNestedPaths gate the destinations?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce static-asset copying at first build: per-dir toggles, ignore globs, and multi-env destination selection.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/server.ts` — onStartServer open 15–29, onBeforeBuild isFirstCompile gate 31–34, publicDir loop 37–60+ (copyOnBuild filter incl. `auto && target!=='node'` 46–53, tinyglobby ignore → fs.copy filter 56–60+).
**Signature:** `api.onBeforeBuild(async ({isFirstCompile, environments}) => ...)`; CopyOptions.filter from glob patterns.
**Data Shape:** server.publicDir: Array<{name, watch?, copyOnBuild?: boolean | 'auto', ignore?: string[]}>.

### Decisive source
```ts
const distPaths = dedupeNestedPaths(
  Object.values(environments)
    .filter(({config}) => copyOnBuild === true || (copyOnBuild === 'auto' && config.output.target !== 'node'))
    .map(({distPath}) => distPath),
);
```
```ts
if (ignore?.length) {
  const { globSync } = await import('tinyglobby');
  // build a filter fn so fs.cp-style copying skips matched RELATIVE paths
```

**Flow:** copies run ONCE (isFirstCompile) inside the BUILD hook — dev-mode requests are served from source publicDir by the middleware instead, which is why watch exists separately. 'auto' means "copy for browser-ish targets only" because node servers read public assets from disk relative to cwd; forcing true copies into server dists too.
**Invariant:** (1) isFirstCompile gate or every rebuild re-copies over user-edited dist files; (2) destination list MUST be deduped-nested or overlapping env dists double-copy and race; (3) ignore patterns match paths RELATIVE to the public dir root, not absolute.
**Probe:** e2e `cases/server/public-dir*` family (copy, ignore, watch, auto-target cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginServer publicDir copyOnBuild dedupeNestedPaths onBeforeBuild", limit: 8 });
```

## Verdict
Adopt first-compile-only copying with auto-target filtering and nested-dedupe destinations. Adapt glob engine to host deps. Omit the browser-open branch (UX surface).
