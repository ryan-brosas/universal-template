<!-- capsule-v2 -->
# Angular-CLI vitest sourcemap path repair — how do you navigate from a built dist file back to the real source when error stacks and test paths point at build output?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145` (vitest-intellij helper); Codebase Memory `jetbrains-webstorm`. **Question:** Angular+Vitest reports paths like `dist/test-out/<uuid>/src/app/app.spec.ts` — what heuristic restores clickable source paths without a full sourcemap VLQ decoder?

## Chunked 'sources' scrape + src-suffix rebase
**Path/Symbol:** `plugins/javascript-plugin/helpers/vitest-intellij/vitest-intellij-file-path-resolver.js` — `getSourcesFiledFromSourcemapFile` (:10-90, 1KB chunks, 1MB abandon limit, hand-rolled bracket/string scanner), `tryResolveOriginFilepathFromItsSourceMaps` (:98-120, `<file>.map` sibling, sources[0], must exist on disk), `VitestIntellijFilePathResolver.resolve` (:125-139, active ONLY under `_JETBRAINS_VITEST_IS_NG_CLI_CONTEXT==='true'`, cache-per-session). Stack repair = `vitest-intellij-util.js:fixErrorStacktraceForAngularCli` (:241-267, first `\s+at\s` frame, shift segments until `'src'`, rejoin under cwd).
**Signature:** `resolve(filePath: string): string`; `fixErrorStacktraceForAngularCli(stacktrace: string): string`.
**Data Shape:** resolver returns ORIGINAL path when context flag absent (zero overhead), when no `.map` exists, parse fails, or resolved source missing; cache memoizes per session (`clearCache()` on testing start).

### Decisive source
```js
while (!sourcesFound) {
  … read 1024-byte chunk, accumulate …
  const sourcesMatch = /"sources"\s*:\s*\[/.exec(accumulatedData);
  if (sourcesMatch) { /* scan with inString/escapeNext tracking until bracket depth 0 */ }
  if (!sourcesFound && accumulatedData.length > 1000000) { break; }   // give up, don't OOM
}
… if (!sourceFilePath.startsWith(PROJECT_ROOT_DIR)) {
    sourceFilePath = path.join(PROJECT_ROOT_DIR, sourceFilePath); }
if (fs.existsSync(sourceFilePath)) { return sourceFilePath; }
```

**Flow:** reporter resolves EVERY task filepath through the resolver → in Angular context, probe `<file>.map`, extract just the `sources` array by streaming scan → take sources[0], rebase onto project root, verify existence → use as node identity/locationHint → same repair applied to the FIRST stack frame so IDE console links resolve.
**Invariant:** every fallback returns the INPUT path unchanged — repair is best-effort and can never make navigation worse. Wrong port: JSON.parsing whole sourcemaps (multi-MB, defeats the purpose), or trusting sources[0] without an existence check (build-only environments would blank out paths).
**Probe:** deterministic source pins: `/"/sources"\s*:\s*\[/` regex present once; `1000000` abandon threshold; `_JETBRAINS_VITEST_IS_NG_CLI_CONTEXT` env gate read at module load (`IS_ANGULAR_CLI_CONTEXT` const). No runner scenario ships for the full Angular pipeline (needs angular-cli) — recorded honestly.
**Coverage caveat:** behavior battery covers the util/connector planes; this file is verified by source inspection only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "VitestIntellijFilePathResolver", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the existence-checked, cached, chunk-scraped sourcemap probe for any bundler→IDE navigation gap. Adapt the `'src'`-suffix heuristic to your output layout convention. Omit the stack-frame rewrite if your host navigates from locationHint alone.
