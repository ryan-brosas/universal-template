<!-- capsule-v2 -->
# Compiler hooks bridge — how do rsbuild's before/after build hooks map onto Rspack run/watchRun/done across a MultiCompiler?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know why one shared `beforeCompile` promise latch is needed per invalidation, and how "all environments done" stays correct when sub-compilers finish repeatedly in watch mode.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/hooks.ts:onBeforeCompile` (242–286), `onCompileDone` (288–341), `registerBuildHook` (343–425), `registerDevHook` (427–506).
**Signature:** `registerBuildHook({context, isWatch, compiler, rspackConfigs, MultiStatsCtor}): void`; dev variant identical minus isWatch (forced true).
**Data Shape:** per-registration closure state: `isFirstCompile: boolean`; inside onCompileDone `compilerStats: Stats[]`, `doneCompilers: number`, per-compiler `compilerDone` flags.

### Decisive source
```ts
// MultiCompiler before-compile: ONE latch shared across all sub-compilers per invalidation
if (isMultiCompiler(compiler)) {
  const { compilers } = compiler;
  let waitBeforeCompileDone: Promise<void> | undefined;
  compiler.hooks.invalid.tap(name, () => { waitBeforeCompileDone = undefined; }); // re-arm
  for (let index = 0; index < compilers.length; index++) {
    const runHook = isWatch ? compilers[index].hooks.watchRun : compilers[index].hooks.run;
    runHook.tapPromise(name, async () => {
      if (!waitBeforeCompileDone) { waitBeforeCompileDone = beforeCompile(); } // first starter wins
      await waitBeforeCompileDone;                    // everyone awaits the same promise
      await beforeEnvironmentCompile(index);          // env hook gets its own buildIndex
    });
  }
}
```
```ts
// MultiCompiler done aggregation with re-arm on invalid
compiler.hooks.done.tapPromise('rsbuild:done', async (stats) => {
  if (!compilerDone) { compilerDone = true; doneCompilers++; }  // idempotent per round
  compilerStats[compilerIndex] = stats;                          // positional write by index
  const lastCompilerDone = doneCompilers === compilers.length;
  await onEnvironmentDone(index, stats);
  if (lastCompilerDone) { await onDone(new MultiStatsCtor(compilerStats)); }
});
compiler.hooks.invalid.tap('rsbuild:done', () => {
  if (compilerDone) { compilerDone = false; doneCompilers--; }   // decrement, not reset-to-zero
});
```

**Flow:** registration happens once after compiler creation. Before side: global `onBeforeBuild.callBatch` fires once per compilation round via the shared latch (sub-compilers starting concurrently don't double-fire), then each environment gets `onBeforeEnvironmentCompile` indexed by sub-compiler position so taps can read `rspackConfigs[buildIndex]`. Done side: each sub-compiler's done writes its stats positionally and fires `onAfterEnvironmentCompile` immediately; the LAST completion composes a fresh `MultiStats` from the collected array and fires `onAfterBuild` once. Watch-mode invalidation resets both latches — done flags are decremented (not zeroed) so out-of-order invalid/done interleavings keep the count exact. `isFirstCompile` flips to false only after the `onAfterBuild` batch resolves.

**Invariant:** environment hooks must never fire for an environment whose global hook hasn't completed (`await waitBeforeCompileDone` ordering comment in source); done-aggregation must be idempotent against spurious repeat-done calls from ts-checker-style plugins.

**Probe:** `e2e/cases/plugin-api/plugin-hooks/index.test.ts:6-33` pins the full build hook sequence verbatim (Modify→…→BeforeBuild→BeforeEnvironmentCompile→ModifyHTMLTags→ModifyHTML→AfterEnvironmentCompile→AfterBuild→CloseBuild); `:32-63` and `:65-110` pin the same ladder for dev with the documented AfterStartDevServer race note.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "onBeforeCompile onCompileDone registerBuildHook registerDevHook MultiCompiler", limit: 10 });
```

## Verdict
Adopt the latch-per-invalidation pattern and positional done-counting with decrement-rearm for any multi-target bundler bridge. Adapt hook payload shapes to host stats types. Omit rsbuild's specific stats serialization (covered in helpers capsules). Coverage caveat: e2e probes require Playwright runner — recorded as deterministic evidence only.
