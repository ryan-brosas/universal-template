<!-- capsule-v2 -->
# Reporter event bridge — how do raw worker task packs/events become ordered reporter callbacks with a correct run-end reason?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How is the worker-side task-event stream translated into the public reporter API, and what decides 'interrupted' vs 'failed' vs 'passed'?

## TestRun
**Path/Symbol:** `packages/vitest/src/node/test-run.ts:TestRun` (29–328) — `end` (118–157), `updated` (93–107), `reportEvent` (207–288), `syncUpdateStacks` (168–205).
**Signature:** `start(specifications)`, `enqueued(project, file)`, `collected(project, files)`, `log(log)`, `updated(update: TaskResultPack[], events: TaskEventPack[])`, `end(specifications, errors: unknown[], coverage?)`.
**Data Shape:** worker stream = arrays of `[taskId, result, meta]` packs + `[taskId, eventName, data]` events; event names are strings like `suite-prepare`, `suite-finished`, `suite-failed-early`, `test-prepare`, `test-finished`, `test-cancel`, `test-retried`, `before-hook-start/end`, `after-hook-start/end`.

### Decisive source
```ts
async end(specifications, errors, coverage) {
  if (coverage) { await this.vitest.report('onCoverage', coverage) }
  // specification won't have the File task if they were filtered by the --shard command
  const modules = specifications.map(spec => spec.testModule).filter(s => s != null)
  const state: TestRunEndReason = this.vitest.isCancelling
    ? 'interrupted'
    : this.hasFailed(modules) ? 'failed' : 'passed'
  if (state !== 'passed') { process.exitCode = 1 }
  await this.vitest.report('onTestRunEnd', modules, [...errors] as SerializedError[], state)
}
```
And the skipped-module replay inside `reportEvent`:
```ts
if (event === 'suite-finished') {
  if (entity.state() === 'skipped') {
    // everything inside a module/suite is skipped,
    // so we won't get any children events — report everything manually
    await this.reportChildren(entity.children)
  }
  ...
}
```

**Flow:** worker packs first go through `syncUpdateStacks` (every serialized error ALWAYS gets a `stacks` array — browser pool uses `project.browser.parseErrorStacktrace`, node uses `parseErrorStacktrace` with an on-demand external-file sourcemap lookup), then `state.updateTasks`, then each event maps to exactly one reporter callback (`suite-prepare`→`onTestModuleStart`/`onTestSuiteReady`, `test-prepare`→`onTestCaseReady`, hook events→`onHookStart/End` with beforeAll/afterEach inferred from entity type); reporter exceptions are captured via `state.catchError(..., 'Unhandled Reporter Error')`.

**Invariant:** (1) cancel status outranks failure — an interrupted run reports 'interrupted' even with failing tests; (2) shard-filtered specs (no File task) are dropped from the end payload rather than crashing; (3) a skipped module emits a full synthetic Ready/Result walk of its children so reporters always see paired start/end events; (4) errors never lack `stacks`.

**Probe:** `test/e2e/test/reported-tasks.test.ts` and `test/e2e/test/cancel-run.test.ts` (:63+) pin callback ordering and interrupted-state reporting; `test/e2e/test/shard.test.ts` pins shard filtering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "TestRun end reportEvent syncUpdateStacks interrupted", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.node.test-run.TestRun
```

## Verdict
Adopt the pack/event → callback bridge with synthetic child replay for skipped containers and the interrupt>fail>pass end-reason precedence. Adapt event-name vocabulary and stack-parsing backends to the host. Omit attachment/artifact resolution (file copying into attachmentsDir) unless the host supports test artifacts.
