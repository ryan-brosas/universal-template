<!-- capsule-v2 -->
# In-worker test executor — what is the exact retry/repeat/hook/fixture execution order inside a test, and how do failures of each stage classify?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** What exact per-attempt order does a test runner follow (aroundEach → beforeEach → fn → afterEach → cleanups → onFinished/onFailed), and when does a retry actually re-run?

## runTest attempt ladder
**Path/Symbol:** `packages/vitest/src/runtime/runner/run.ts:runTest` (586–787), `failTask` (789–812), `passesRetryCondition` (563–584), `getRetryCount/Delay/Condition` (47–77); suite counterpart `runSuite` (839–976) with `markTasksAsSkipped` (814–823).
**Signature:** `async function runTest(test: Test, runner: VitestRunner): Promise<void>`; nested loops `for repeatCount <= repeats` ⊃ `for retryCount <= retry`.
**Data Shape:** mutates `test.result = { state, startTime, retryCount, repeatCount, duration, errors? }`; terminal states pass/fail/skip; `PendingError` ⇒ skip-with-note; `TestRunAbortError` ⇒ skip.

### Decisive source
```ts
const repeats = test.repeats ?? 0
for (let repeatCount = 0; repeatCount <= repeats; repeatCount++) {
  const retry = getRetryCount(test.retry)
  for (let retryCount = 0; retryCount <= retry; retryCount++) {
    let beforeEachCleanups: unknown[] = []
    await callAroundEachHooks(suite, test, async (fixtureCheckpoint) => {
      beforeEachCleanups = await callSuiteHook(suite, test, 'beforeEach', ...)
      try { ...run the test fn... if (test.result!.state !== 'fail') test.result!.state = 'pass' }
      catch (e) { failTask(test.result!, e, ...) }
      ...
      afterEach + beforeEachCleanups + callFixtureCleanupFrom(context, fixtureCheckpoint)
      onFinished ('stack' sequence) / onFailed (config sequence)
    }).catch(e => failTask(test.result!, e, ...))
    await callFixtureCleanup(test.context)          // aroundEach fixtures, AFTER teardown
    if (test.result?.pending || test.result?.state === 'skip') { ...return... }
    if (test.result.state === 'pass') break         // PASS breaks the retry loop...
    if (retryCount < retry) {
      if (!passesRetryCondition(test, test.result.errors)) break   // condition gate
      test.result.state = 'run'
      test.result.retryCount++
      if (delay > 0) await sleep(delay)
    }
    updateTask('test-retried', test, runner)
  }
}
// after all attempts: test.fails flips the outcome unless __vitest_test_syntax_error__
```

**Flow:** per attempt: aroundEach chain (outermost first) → beforeEach (parent-chain recursive, cleanup fns collected) → test fn under `limitMaxConcurrency` → afterEach chain → beforeEach cleanups → fixtures created inside runTest only (`callFixtureCleanupFrom` at the checkpoint taken before runTest) → aroundEach fixtures cleaned after the whole hook resolves. A failed `beforeAll` fails the SUITE and marks every child skipped; `afterAll` runs in a `finally`. Retry re-runs hooks too because the whole ladder lives inside the retry loop.

**Invariant:** (1) repeats × retries are nested loops — a passing attempt breaks out early; a retry re-executes ALL per-test hooks and clears module mocks/snapshot state via runner `onBeforeTryTask`; (2) `retry.condition` (RegExp on last error message, or predicate) can veto a retry; (3) hook failures fail the TEST but never skip later cleanup stages — each cleanup group has its own try/catch that calls `failTask`; (4) `test.fails` inversion ignores syntax errors.

**Probe:** `test/e2e/test/retry.test.ts` (:13/:19 — "should passed", "retry but still failed" asserting intermediate failure messages for each retry); `retry-condition.test.ts`, `repeats.test.ts`, `execution-order.test.ts` (unit) pin ordering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "runTest passesRetryCondition callAroundHooks markTasksAsSkipped", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.runtime.runner.run.{runTest,passesRetryCondition,failTask}
```

## Verdict
Adopt the nested repeat/retry ladder with full-hook re-execution per attempt, the fixture-checkpoint split (inside-runTest vs aroundEach cleanup), and per-stage error classification. Adapt hook names and concurrency limiter to the host. Omit benchmark-specific bookkeeping (`benchInstances`) and OTel trace spans.
