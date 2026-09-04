<!-- capsule-v2 -->
# Worker timing accumulators — what exactly does netLintingDuration subtract, and where is each term measured?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** How does a worker compute the "net linting" duration the main thread uses for the concurrency notice, and which costs are deliberately excluded?

## Three bigint accumulators in worker.js
**Path/Symbol:** `lib/eslint/worker.js` — `readFileCounter` (:107), `lintingStartTime` (:109), claim loop (:115–157), `loadConfigTotalDuration` accumulation (:126–135), `lintingDuration` (:159), `netLintingDuration` (:165–166), timings attachment (:168–170); read-side accumulation inside `lintFile` at `lib/eslint/eslint-helpers.js` (:1211–1222 param, :1288–1289).
**Signature:** worker posts `IndexedLintResult[] & { netLintingDuration: bigint, timings? }`.
**Data Shape:** all three accumulators are `process.hrtime.bigint()` bigint deltas; `readFileCounter` is a `{ duration: bigint }` object threaded through `lintFile` by reference.

### Decisive source
```js
const lintingStartTime = hrtimeBigint();
for (;;) {
  const loadConfigEnterTime = hrtimeBigint();
  const configs = await configLoader.loadConfigArrayForFile(filePath);
  loadConfigTotalDuration += loadConfigExitTime - loadConfigEnterTime;
  const result = await lintFile(filePath, configs, processedESLintOptions, linter, lintResultCache, readFileCounter);
  ...
}
const lintingDuration = hrtimeBigint() - lintingStartTime;
indexedResults.netLintingDuration =
  lintingDuration - loadConfigTotalDuration - readFileCounter.duration;
```

**Flow:** per file, config-load time is measured around `loadConfigArrayForFile`; file-read time is measured inside `lintFile`'s `readAndVerifyFile` and added to the shared counter object; the whole loop is bracketed by `lintingStartTime`/`lintingDuration`. The difference is the only thing the worker reports as "net".
**Invariant:** `netLintingDuration` excludes exactly the two costs that do NOT scale with parallelism — config loading (cached and shared across files) and file I/O (I/O-bound) — leaving the CPU-bound lint computation that the main thread's net-linting-ratio notice compares against wall-clock time (`eslint.js:497` divides `Number(indexedResults.netLintingDuration)` into the run total). Accumulators are bigint so long runs cannot lose precision; the `readFileCounter` object is shared by reference so `lintFile` can accumulate without a return channel. `timing.getData()` rides the same postMessage when TIMING is enabled (see timing-merge-display for the merge side).
**Probe:** `tests/lib/eslint/eslint.js` calculateWorkerCount suite (:12932–13139) exercises workers end-to-end; net-linting-ratio-concurrency capsule documents the consumer side. Live probe this pass: direct byte-matched read of `worker.js:107–172` at the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "netLintingDuration readFileCounter loadConfigTotalDuration worker", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.eslint.worker" });
```

## Verdict
Adopt the subtract-the-unchangeable-costs decomposition for any worker-pool efficiency metric; adapt which costs count as "fixed" for your host; omit bigint precision only if your runs are short. Caveat: Codebase Memory MCP was not connected in the mining session; anchors verified by direct byte-matched source reads at the git-clean pin.
