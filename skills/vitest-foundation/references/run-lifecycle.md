<!-- capsule-v2 -->
# Test-run lifecycle — how does a driver serialize runs, wait out the previous run, and guarantee end-of-run reporting even when the pool throws?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How does the orchestrator make overlapping run requests safe and ensure coverage/reporting always fire exactly once per run?

## Single-flight run loop in `Vitest.runFiles`
**Path/Symbol:** `packages/vitest/src/node/core.ts:Vitest.runFiles` (989–1058), consumed via public entry points `start()` (802–881), `runTestSpecifications` (954–957), `rerunTestSpecifications`, `collectTests` (1170–1222).
**Signature:** `private async runFiles(specs: TestSpecification[], allTestsRun: boolean): Promise<TestRunResult>` — wrapped by every public entry.
**Data Shape:** resolves to `{ testModules: this.state.getTestModules(), unhandledErrors: this.state.getUnhandledErrors() }`. Instance fields `runningPromise`, `cancelPromise`, `isCancelling`, `isFirstRun`, `pool` carry cross-call state; `this._testRun` (a `TestRun`) owns reporter events.

### Decisive source
```ts
await this._testRun.start(specs)
await this.coverageProvider?.onTestRunStart?.()

// previous run
await this.cancelPromise
await this.runningPromise
this._onCancelListeners.clear()
this.isCancelling = false

// schedule the new run
this.runningPromise = (async () => {
  try {
    if (!this.pool) { this.pool = createPool(this) }
    const invalidates = Array.from(this.watcher.invalidates)
    this.watcher.invalidates.clear()
    this.snapshot.clear()
    this.state.clearErrors()
    ...
    await this.initializeGlobalSetup(specs)
    try {
      await this.pool.runTests(specs, invalidates)
    }
    catch (err) {
      this.state.catchError(err, 'Unhandled Error')   // pool failure becomes a reported error, not a crash
    }
    ...cache results...
  }
  finally {
    const coverage = await this.coverageProvider?.generateCoverage({ allTestsRun })
    const errors = this.state.getUnhandledErrors()
    this._checkUnhandledErrors(errors)                 // sets process.exitCode = 1 unless dangerouslyIgnoreUnhandledErrors
    await this._testRun.end(specs, errors, coverage)
    await this.reportCoverage(coverage, allTestsRun)
  }
})().finally(() => {
  this.runningPromise = undefined
  this.isFirstRun = false
  // all subsequent runs will treat this as a fresh run
  this.config.changed = false
  this.config.related = undefined
})
return await this.runningPromise
```

**Flow:** `onTestRunStart` → drain previous `cancelPromise` then previous `runningPromise` → reset cancel listeners/state errors/watch invalidations → global setup per touched project → `pool.runTests` (exceptions captured into StateManager as `'Unhandled Error'`) → write results cache → **finally**: generate coverage, `_testRun.end(...)` fires `onTestRunEnd`, report coverage → clear `runningPromise`, flip `changed`/`related` off so later runs are fresh.

**Invariant:** (1) at most ONE run is ever in flight — a second caller awaits both prior promises before scheduling, so state mutation never overlaps; (2) the `finally` guarantees `onTestRunEnd` + coverage generation fire exactly once per run even when the pool rejects; (3) pool exceptions are converted to state errors (`state.catchError`) rather than escaping, but reporter/coverage failures still surface; (4) `--changed`/`--related` apply only to the first run of the session.

**Probe:** `test/e2e/test/cancel-run.test.ts` (`cancelCurrentRun('keyboard-input')` mid-run ⇒ run ends with interrupted modules, `afterEach` still executed); `test/e2e/test/bail-race.test.ts`; watch-mode reruns in `test/e2e/test/watch/file-watching.test.ts` pin that a rerun after completion starts clean. Coverage caveat: tests live under `test/` which IS indexed in full mode, but probes were read on disk at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "runFiles runningPromise cancelPromise test_run", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.node.core.Vitest.runFiles / .cancelCurrentRun / .start
```

## Verdict
Adopt the single-flight promise pattern (await-previous-then-schedule), try/finally end-of-run reporting, and pool-error→state-error conversion. Adapt field names and the coverage hook points to the host. Omit Vite-specific plumbing (`_traces` spans, `configOverride` merging) unless the host has an equivalent config layer.
