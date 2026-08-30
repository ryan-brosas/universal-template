<!-- capsule-v2 -->
# Net-linting-ratio concurrency feedback — how do you measure whether worker threads were worth spinning up?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** How does the orchestrator detect that parallelism didn't pay (I/O-bound workloads) and warn the user with advice matched to HOW they chose concurrency?

## netLintingDuration accounting + worst-ratio warning + notice trichotomy
**Path/Symbol:** `lib/eslint/worker.js` (:159–166 netLintingDuration bigint subtraction), `lib/eslint/eslint.js`: `runWorkers` (:456–545: LOW_NET_LINTING_RATIO :446, per-worker ratio :496–503, abort wiring :521, timing.disableDisplay on failure :536, warning trigger :539–540), stub seam `module.exports.calculateWorkerCount` consulted THROUGH the module object (:1043–1047, export at file tail), notice TRICHOTOMY selected in lintFiles BEFORE workers start (:1048–1060), `emitPoorConcurrencyWarning` (`lib/services/warning-service.js:79–84`, template `` `You may ${notice} to improve performance.` ``).
**Signature:** `runWorkers(filePaths, workerCount, optionsOrURL, warnOnLowNetLintingRatio)`; results array indexed via `SharedArrayBuffer` Uint32 counter; `emitPoorConcurrencyWarning(notice: string)`.
**Data Shape:** each worker posts `IndexedLintResult[] & {netLintingDuration: bigint, timings?}`; ratio = `Number(netLintingDuration) / Number(workerDuration)`; threshold `LOW_NET_LINTING_RATIO = 0.7`.

### Decisive source
```js
// worker side — SUBTRACT the un-parallelizable I/O from the thread's wall time:
indexedResults.netLintingDuration = lintingDuration - loadConfigTotalDuration - readFileCounter.duration;
// main side — track the WORST worker, not the average:
worstNetLintingRatio = Math.min(worstNetLintingRatio, netLintingRatio);
...
if (worstNetLintingRatio < LOW_NET_LINTING_RATIO) warnOnLowNetLintingRatio();

// lintFiles — the advice depends on how concurrency was chosen, decided BEFORE spawn:
// The value of `module.exports.calculateWorkerCount` can be overridden in tests.
const workerCount = module.exports.calculateWorkerCount(this, filePaths);
if (workerCount) {
    let poorConcurrencyNotice;
    if (workerCount <= 2) {
        poorConcurrencyNotice = "disable concurrency";
    } else if (concurrency === "auto") {
        poorConcurrencyNotice = "disable concurrency or use a numeric concurrency setting";
    } else {
        poorConcurrencyNotice = "reduce or disable concurrency";
    }
    results = await lintFilesWithMultithreading(this, filePaths, workerCount, this.#optionsOrURL,
        () => warningService.emitPoorConcurrencyWarning(poorConcurrencyNotice));
}
```

**Flow:** workers self-time config-loading and file-reading (bigint accumulators) → post net duration with index-tagged results → main computes per-worker ratios as messages arrive, takes the MINIMUM → below 0.7 triggers the closure passed in from lintFiles, whose TEXT was already selected before any worker started: `workerCount <= 2` ⇒ "disable concurrency" (a 2-worker pool can't be reduced — only off); `concurrency === "auto"` ⇒ "disable concurrency or use a numeric concurrency setting"; explicit numeric >2 ⇒ "reduce or disable concurrency".
**Invariant:** MIN-of-workers (not mean): one starved worker proves the pool misconfigured. Timing display is suppressed (`timing.disableDisplay()`) if ANY worker throws, so partial/missing tables never print. Worker failure aborts siblings through a shared AbortController that terminates every worker. The subtraction defines the metric precisely: only computation-intensive, non-duplicated work counts toward "was threading useful". The trichotomy is selected in lintFiles (not runWorkers) because it needs the user's ORIGINAL concurrency choice, which runWorkers no longer sees; `module.exports.calculateWorkerCount` is consulted through the module object precisely so tests/tools can stub the partition without touching the heuristic.
**Probe:** `tests/lib/services/warning-service.js:90–101` (template pinned: `You may ${notice} to improve performance.`); `tests/lib/eslint/eslint.js` (:12932–13139 calculateWorkerCount truth table incl. numeric 1⇒0, auto cores/2 cap, ignored-file exclusion — suite also exercises the stub seam by constructing real instances; :4230–4290 et al. stub emitPoorConcurrencyWarning in multithreaded tests). Live probes this pass — ALL THREE arms triggered end-to-end: `concurrency: 2` over 3 files (workerCount 2 ≤ 2) → `ESLintPoorConcurrencyWarning: You may disable concurrency to improve performance.`; `concurrency: 4` over 3 files (workerCount 3, numeric) → `You may reduce or disable concurrency to improve performance.`; `concurrency: "auto"` over 150 files on 32 cores (workerCount 3) → `You may disable concurrency or use a numeric concurrency setting to improve performance.` Mocha subset `tests/lib/services/warning-service.js` → 7 passing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "runWorkers netLintingDuration emitPoorConcurrencyWarning calculateWorkerCount", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.services.warning-service.WarningService.emitPoorConcurrencyWarning" });
```

## Verdict
Adopt the metric definition + min-of-workers rule for any worker pool whose value depends on workload shape; adapt threshold. Adopt the pre-spawn advice trichotomy: the warning text must be chosen where the user's original setting is still visible, and the smallest-pool arm ("just turn it off") must exist separately from the reducible arms. Omit the SharedArrayBuffer indexing if you batch statically. Caveat: Codebase Memory MCP was not connected in the mining session; anchors verified by direct byte-matched source reads at the git-clean pin.
