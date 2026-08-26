<!-- capsule-v2 -->
# Net-linting-ratio concurrency feedback — how do you measure whether worker threads were worth spinning up?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does the orchestrator detect that parallelism didn't pay (I/O-bound workloads) and warn the user with an actionable hint?

## netLintingDuration accounting + worst-ratio warning
**Path/Symbol:** `lib/eslint/worker.js` (:160–170 netLintingDuration), `lib/eslint/eslint.js:runWorkers` (:456–545: LOW_NET_LINTING_RATIO :446, per-worker ratio :496–503, abort wiring :521, timing.disableDisplay on failure :536, warning trigger :539–540) + `emitPoorConcurrencyWarning` (`warning-service.js:79`) + notice text selection (eslint.js:1048–1067).
**Signature:** `runWorkers(filePaths, workerCount, optionsOrURL, warnOnLowNetLintingRatio)`; results array indexed via `SharedArrayBuffer` Uint32 counter.
**Data Shape:** each worker posts `IndexedLintResult[] & {netLintingDuration: bigint, timings?}`; ratio = `Number(netLintingDuration) / Number(workerDuration)`; threshold `LOW_NET_LINTING_RATIO = 0.7`.

### Decisive source
```js
// worker side — SUBTRACT the un-parallelizable I/O from the thread's wall time:
indexedResults.netLintingDuration = lintingDuration - loadConfigTotalDuration - readFileCounter.duration;
// main side — track the WORST worker, not the average:
worstNetLintingRatio = Math.min(worstNetLintingRatio, netLintingRatio);
...
if (worstNetLintingRatio < LOW_NET_LINTING_RATIO) warnOnLowNetLintingRatio();
```

**Flow:** workers self-time config-loading and file-reading → post net duration with indexed results → main computes per-worker ratios as messages arrive, takes the minimum → below-threshold triggers a warning whose TEXT depends on how concurrency was chosen ("disable concurrency or use a numeric concurrency setting" for auto vs "reduce or disable concurrency" when explicitly numeric).
**Invariant:** MIN-of-workers (not mean): one starved worker proves the pool misconfigured. Timing display is suppressed (`timing.disableDisplay()`) if ANY worker throws, so partial/misleading tables never print. Worker failure aborts siblings through a shared AbortController that terminates every worker. The subtraction defines the metric precisely: only computation-intensive, non-duplicated work counts toward "was threading useful".
**Probe:** `tests/lib/eslint/eslint.js` (:4230–4290 poor-concurrency-warning stubbing in multithreaded tests); `tests/lib/services/warning-service.js:90` (typed warning text). Live end-to-end ratio behavior is CLI-level (caveat: no dedicated unit test for runWorkers itself at this pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "runWorkers netLintingDuration emitPoorConcurrencyWarning", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.services.warning-service.WarningService.emitPoorConcurrencyWarning" });
```

## Verdict
Adopt the metric definition + min-of-workers rule for any worker pool whose value depends on workload shape; adapt threshold; omit the SharedArrayBuffer indexing if you batch statically.
