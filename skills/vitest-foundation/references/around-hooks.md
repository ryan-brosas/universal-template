<!-- capsule-v2 -->
# Around-hooks protocol — how do aroundEach/aroundAll wrap inner execution with separate setup/teardown timeouts and a strictly-single-use callback?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How can an "around" hook (receives a `run` callback) enforce that the callback is called exactly once and that setup vs teardown each get their own timeout budget?

## callAroundHooks state machine
**Path/Symbol:** `packages/vitest/src/runtime/runner/run.ts:callAroundHooks` (265–441), `makeAroundHookTimeoutError` (250–263), consumers `callAroundAllHooks` (443–453) / `callAroundEachHooks` (455–473); error classes in `runtime/runner/errors.ts` (`AroundHookMultipleCallsError`, `AroundHookSetupError`, `AroundHookTeardownError`).
**Signature:** `async function callAroundHooks<THook extends Function>(runInner: () => Promise<void>, options: { hooks; hookName: 'aroundEach'|'aroundAll'; callbackName: 'runTest()'|'runSuite()'; onTimeout?: (error) => void; invokeHook: (hook, use: () => Promise<void>) => Awaitable<unknown> })`.
**Data Shape:** per hook: `useCalledPromise`, `useReturnedPromise`, `hookCompletePromise`, plus two lazily-created timeout promises (`setupTimeout`, `teardownTimeout`) built from `createTimeoutPromise(timeout, phase, stackTraceError)`.

### Decisive source
```ts
const use = async () => {
  // shouldn't continue to next when aroundEach/All setup timed out.
  if (setupTimeout.isTimedOut()) {
    throw new Error('__VITEST_INTERNAL_AROUND_HOOK_ABORT__')  // unseen by users
  }
  if (useCalled) {
    throw new AroundHookMultipleCallsError(
      `The \`${callbackName}\` callback was called multiple times in the \`${hookName}\` hook. ...`)
  }
  useCalled = true
  resolveUseCalled()
  setupTimeout.clear()
  await runNextHook(index + 1).catch(e => hookErrors.push(e))
  teardownLimitConcurrencyRelease = await limitMaxConcurrency.acquire()
  teardownTimeout = createTimeoutPromise(timeout, 'teardown', stackTraceError)  // timer starts AFTER inner completes
  resolveUseReturned()
}
setupLimitConcurrencyRelease = await limitMaxConcurrency.acquire()
setupTimeout = createTimeoutPromise(timeout, 'setup', stackTraceError)
;(async () => { try {
    await invokeHook(hook, use)
    if (!useCalled) throw new AroundHookSetupError(`The \`${callbackName}\` callback was not called ...`)
    resolveHookComplete()
  } catch (error) { rejectHookComplete(error) }
  finally { setupLimitConcurrencyRelease?.(); teardownLimitConcurrencyRelease?.() } })()

await Promise.race([useCalledPromise, hookCompletePromise, setupTimeout.promise])
await Promise.race([useReturnedPromise, hookCompletePromise])
await Promise.race([hookCompletePromise, teardownTimeout?.promise])
```

**Flow:** run the hook body in the background holding one concurrency slot → race (callback-called | hook-completed | setup-timeout): timeout ⇒ `AroundHookSetupError`, `onTimeout` aborts the test context signal, and any later `use()` bails via the internal sentinel error → race (inner-finished | hook-error) → start teardown timer only after the inner chain completed → race (hook-complete | teardown-timeout) ⇒ `AroundHookTeardownError`. Errors accumulate in `hookErrors` and are thrown as an array at the end.

**Invariant:** (1) `use()` is single-shot — second call is a loud `AroundHookMultipleCallsError`; never calling it is `AroundHookSetupError`; (2) setup and teardown timeouts are SEPARATE budgets — the teardown clock cannot consume time spent running inner hooks/tests; (3) timeout errors keep the USER's stack frame by string-replacing the message over `stackTraceError.stack`; (4) aroundEach fixtures resolved before `runTest` survive test-scoped cleanup (checkpoint passed through `getFixtureCleanupCount`).

**Probe:** `test/e2e/test/around-each.test.ts` (:8 basic wrapping, :33 multiple hooks nest first-outermost, :69 nested suites); `test/e2e/test/hook-timeout.test.ts` pins timeout classification.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "callAroundHooks AroundHookMultipleCallsError AroundHookSetupError", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.runtime.runner.run.callAroundHooks
```

## Verdict
Adopt the three-race state machine with split phase timeouts and single-use callback enforcement for ANY callback-style wrapper API. Adapt error class names and concurrency integration to the host. Omit the fixture-checkpoint plumbing unless porting vitest's fixture system wholesale.
