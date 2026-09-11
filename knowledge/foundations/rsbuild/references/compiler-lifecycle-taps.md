<!-- capsule-v2 -->
# Compiler lifecycle taps + build-state machine — why does watchRun own the "building" log and done() own the time print?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the run/watchRun/invalid/done tap matrix, lazy-module log mining, and MultiCompiler per-child time printing.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/createCompiler.ts` — version gate 100–106, unsafeFastDrop 111–114, infrastructureLog lazy-mining 126–149, run 153–156, watchRun 158–172, invalid 174–178, first-compiler-only build log 180–190, `printTime` 192–210, per-child done 212–218, aggregate done 220–242, dev-hook registration 244–251.
**Signature:** `createCompiler(options): Promise<{compiler, rspackConfigs}>`.
**Data Shape:** context.buildState `{status:'building'|'idle'|'done', stats, hasErrors, time: Record<envName,ms>}`; lazyModules Set<string>.

### Decisive source
```ts
compiler.hooks.infrastructureLog.tap(HOOK_NAME, (name, _, args) => {
  if (name === 'LazyCompilation' && typeof args[0] === 'string' && args[0].startsWith(LAZY_COMPILATION_IDENTIFIER)) {
    const absolutePath = args[0].split(' ')[0].split('!').pop();
    if (absolutePath?.startsWith(rootPath)) lazyModules.add(absolutePath.replace(rootPath, ''));
  }
});
```
```ts
compiler.hooks.watchRun.tap(HOOK_NAME, (compiler) => {
  startTime = Date.now(); context.buildState.status = 'building'; logRspackVersion();
  if (!isCompiling) printBuildLog(compiler, context, lazyModules);   // changed → lazy → removed fallback chain
  if (lazyModules.size) lazyModules.clear();
  isCompiling = true;
});
compiler.hooks.done.tap(HOOK_NAME, (statsInstance) => {   // aggregate done fires ONCE per rebuild
  const stats = getRsbuildStats(statsInstance, compiler, logger, options.context.action);
  context.buildState.stats = stats; status='done'; hasErrors=...;
  context.socketServer?.onBuildDone();                     // HMR fan-out rides the same latch
  ...formatStats message by level; if (!isMultiCompiler) printTime(0, hasErrors);
  isCompiling = false;
});
```

**Flow:** removed-files builds whose paths ALL contain 'virtual' print "building virtual modules" (#11694 workaround). Per-child compilers each get a done→printTime(index) so multi-env builds show `(web)` / `(node)` suffixes; the AGGREGATE done skips printTime in that case to avoid doubles. Version logging is once-per-process via boolean latch. onBeforeCreateCompiler/onAfterCreateCompiler bracket rspack() construction with callBatch.
**Invariant:** (1) buildState.status transitions must be driven ONLY by these four taps or HMR/socket consumers race; (2) infrastructureLog parsing must tolerate loader-chain suffixes (`resource!loader`) via split('!').pop(); (3) printBuildLog's priority changed>lazy>removed keeps human-meaningful output when several sets are populated.
**Probe:** unit `packages/core/tests/builder.test.ts` (default bundler + nested plugins), snapshot suites hooks.test.ts; e2e `cases/basic`, `cases/lazy-compilation/*` pin observable logs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "createCompiler watchRun infrastructureLog printTime registerDevHook", limit: 8 });
```

## Verdict
Adopt the four-tap state machine, lazy-compilation log scraping, per-child timing with single aggregate latch, and socket fan-out at done. Adapt hook names to your bundler (webpack identical, esbuild differs). Omit RSPACK_UNSAFE_FAST_DROP unless targeting rspack.
