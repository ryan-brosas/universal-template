<!-- capsule-v2 -->
# Bail as a cross-process failure budget — how does `bail: N` stop a parallel run without double-counting or racing?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b35847`); Codebase Memory `vitest`. **Question:** When several workers fail tests simultaneously, who decides the run is over, and why doesn't the budget overshoot or deadlock?

## Worker-side trigger patch in `resolveTestRunner`
**Path/Symbol:** `packages/vitest/src/runtime/runners/index.ts:resolveTestRunner` (onAfterRunTask patch, ~139–152); server side `packages/vitest/src/node/state.ts:StateManager.getCountOfFailedTests` (257–261); node sink `packages/vitest/src/node/core.ts:Vitest.cancelCurrentRun` (1245–1251); RPC glue `packages/vitest/src/node/pools/rpc.ts` (339–344) and `packages/vitest/src/runtime/rpc.ts:onCancel` (85–87).
**Signature:** `testRunner.onAfterRunTask = async (test: Task) => void` (patched over the runner's own hook).
**Data Shape:** reads `config.bail` (number|true, serialized to workers via `serializeConfig.ts:21 bail: config.bail`) and `test.result?.state`; asks main via RPC for an integer; emits cancel reason `'test-failure'` on two channels.

### Decisive source
```ts
const originalOnAfterRunTask = testRunner.onAfterRunTask
testRunner.onAfterRunTask = async (test) => {
  if (config.bail && test.result?.state === 'fail') {
    const previousFailures = await rpc().getCountOfFailedTests()
    const currentFailures = 1 + previousFailures   // self-count closes the race window
    if (currentFailures >= config.bail) {
      rpc().onCancel('test-failure')
      testRunner.cancel?.('test-failure')          // stop this worker's remaining tasks too
    }
  }
  await originalOnAfterRunTask?.call(testRunner, test)
}
```
Server counter (authoritative, scans the live task tree):
```ts
getCountOfFailedTests(): number {
  return Array.from(this.idMap.values()).filter(t => t.result?.state === 'fail').length
}
```

**Flow:** worker finishes a task → sees local failure → RPC round-trip "how many failures does the tree already hold?" → add its own +1 (its result has not reached main yet) → if ≥ bail, request cancel twice: node-side (`cancelCurrentRun` sets `isCancelling`, fires listeners, awaits `runningPromise` so nothing is torn down mid-flight) and worker-side (`testRunner.cancel` marks pending tasks skipped). The next worker that hits the budget check sees the updated count.
**Invariant:** (1) bail counts TOTAL failed tests across all files/projects/workers, not per-file; (2) the decision uses main-process state as truth plus a local +1 so two simultaneous first-failures cannot both see "0 previous" forever — but brief overshoot beyond N is accepted by design (parallelism); (3) cancellation stays graceful — no worker is killed mid-test, queued work is marked skipped; (4) with `bail` unset the whole patch costs one falsy branch.

**Probe:** `test/e2e/test/config/bail.test.ts` — matrix over pools {threads,forks,browser} × isolate × fileParallelism asserts `bail:1` prints pass+fail of first file only, every later test skipped, exit code 1. `test/e2e/test/bail-race.test.ts` — five consecutive `createVitest(...bail:1).start()` runs with `maxWorkers:1` must produce ZERO `[vitest-pool]: Cannot run tasks while pool is cancelling` unhandled errors (cancelled runs don't poison the next run).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", name_pattern: "getCountOfFailedTests|onCancel", limit: 10 });
// observed: StateManager.getCountOfFailedTests (node/state.ts 257-261), pools/rpc.ts 342-344,
// Vitest.onCancel (core.ts 1693-1698), runtime/rpc.ts onCancel 85-87, browser rpc twins.
```

## Verdict
Adopt the shape: policy decided against a central live-state counter, workers self-count their in-flight delta, cancel requested through two channels with graceful drain. Adapt the transport (any RPC/queue works) and where "failed" is recorded. Omit vitest's serializeConfig plumbing. Caveat: e2e probes need installed deps; verified here by byte-for-byte source reads at the pinned HEAD (no node_modules in checkout).
