<!-- capsule-v2 -->
# expect.poll kernel — how does an assertion retry itself until a deadline while staying lazy, cancellable, and correctly stack-traced?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b35847`); Codebase Memory `vitest`. **Question:** How do you turn ANY chai-style matcher into an auto-retrying assertion without wrapping each matcher individually, and without leaking "unhandled rejection" or misattributed stacks?

## Proxy chain-starter + poll loop in `createExpectPoll`
**Path/Symbol:** `packages/vitest/src/integrations/chai/poll.ts:createExpectPoll` (47–237), helpers `throwWithCause`/`copyStackTrace` (38–45, 239–244), `raceWith` envelope race (246–258).
**Signature:** `(expect) => poll(fn: (ctx:{signal:AbortSignal}) => unknown, options?: {interval?: number; timeout?: number; message?: string}) => PromiseLike<void>`; defaults from `state.config.expect?.poll ?? {}` → interval 50ms / timeout 1000ms.
**Data Shape:** stores fn/timeout/interval as chai flags `_poll.fn|timeout|interval` on an `expect(null).withContext({poll:true})` assertion; requires flag `vitest-test` (must be called inside a test).

### Decisive source
```ts
const proxy: any = new Proxy(assertion, {
  get(target, key, receiver) {
    const assertionFunction = Reflect.get(target, key, receiver)
    if (typeof assertionFunction !== 'function')
      return assertionFunction instanceof chai.Assertion ? proxy : assertionFunction
    if (key === 'assert') return assertionFunction
    if (typeof key === 'string' && unsupported.includes(key))   // snapshots + toThrow family
      throw new SyntaxError(`expect.poll() is not supported in combination with .${key}(). Use vi.waitFor() ...`)
    return function __VITEST_POLL_CHAIN__(this: any, ...args: any[]) {
      const STACK_TRACE_ERROR = new Error('STACK_TRACE_ERROR')  // captured BEFORE async loop
      const promise = async () => {
        chai.util.flag(assertion, '_name', key)
        chai.util.flag(assertion, 'error', STACK_TRACE_ERROR)
        ...
        const timeoutPromise = new Promise<void>((resolve) => {
          timerId = setTimeout(() => { timeoutController.abort(); resolve() }, timeout)
        })
        let lastError
        try {
          while (true) {
            try {
              const fnResult = await raceWith(Promise.resolve().then(() => fn({ signal: timeoutController.signal })), timeoutPromise)
              if (!fnResult.ok) { lastError ??= new Error(`expect.poll() function didn't resolve in time.`); break }
              chai.util.flag(assertion, 'object', fnResult.value)
              const assertionResult = await raceWith(Promise.resolve().then(() => assertionFunction.apply(assertion, args)), timeoutPromise)
              if (!assertionResult.ok) { lastError ??= new Error(`expect.poll() assertion didn't resolve in time.`); break }
              await onSettled?.({ assertion, status: 'pass' }); return assertionResult.value
            }
            catch (err) {
              lastError = err
              const result = await raceWith(delay(interval, setTimeout), timeoutPromise)
              if (!result.ok) break
              if (vi.isFakeTimers()) vi.advanceTimersByTime(interval)   // faked clocks need manual advance
            }
          }
        } finally { clearTimeout(timerId) }
        if (lastError) { await onSettled?.({ assertion, status: 'fail' }); throwWithCause(lastError, STACK_TRACE_ERROR) }
      }
      let awaited = false
      test.onFinished ??= []; test.onFinished.push(() => {
        if (!awaited) throw copyStackTrace(new Error(`${assertionString} was not awaited. This assertion is asynchronous and must be awaited...`), STACK_TRACE_ERROR)
      })
      return {   // thenable that STARTS the loop only on await
        then(onFulfilled, onRejected) { awaited = true; return (resultPromise ||= promise()).then(onFulfilled, onRejected) },
        catch(onRejected) { awaited = true; return (resultPromise ||= promise()).catch(onRejected) },
        finally(onFinally) { awaited = true; return (resultPromise ||= promise()).finally(onFinally) },
        [Symbol.toStringTag]: 'Promise',
      }
    }
  },
})
```

**Flow:** property read through the proxy classifies: non-function → pass through (`Assertion` instances re-wrapped as proxy for chaining `.to`), `.assert` → raw, unsupported matcher → immediate `SyntaxError`, anything else → replaced by `__VITEST_POLL_CHAIN__`. Calling it captures the stack trace synchronously at the user's callsite, then returns a LAZY thenable: the retry loop starts only when `.then/.catch/.finally` is touched. Each iteration re-runs `fn()` (abortable via signal), installs its value as the assertion's `object`, runs the real matcher once; failure waits `interval` (manually advancing fake timers) and retries until `timeout` fires, which aborts `fn`'s signal and breaks with "didn't resolve in time". Final failure is rethrown with `cause` attached and the pre-captured stack copied over.
**Invariant:** (1) zero per-matcher wrapping — one proxy turns every method into a poll chain; (2) the loop never even starts unless awaited, and a forgotten await fails the TEST at teardown via `test.onFinished` (no silent no-op, no unhandled rejection); (3) reported stacks point at the user's `.toBe…()` line because the trace was captured before entering async land; (4) both `fn` and the matcher are raced against the SAME deadline — either can time out, message distinguishes which; (5) snapshot matchers and toThrow are refused outright (they're semantically wrong under polling); (6) domain-snapshot matchers can take over via a `__vitest_poll_takeover__` own-property flag.

**Probe:** `test/unit/test/expect-poll.test.ts` — cases: simple usage, timeout, interval, "fake timers don't break it", "fake timers are advanced on each poll interval", custom matcher, custom message, unresolved function, unresolved assertion. Caveat: unit suite needs installed deps; source read byte-for-byte at pinned HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", name_pattern: ".*[Pp]oll.*", limit: 15 });
// observed: createExpectPoll + __VITEST_POLL_CHAIN__ (integrations/chai/poll.ts 47-237),
// ExpectPollOptions (types/global.ts 31-35), AssertDomainPollOptions (snapshot/client.ts 54-58),
// direct test test/unit/test/expect-poll.test.ts.
```

## Verdict
Adopt the proxy→chain-starter pattern, lazy thenable with await-enforcement hook, envelope race (`{ok,value}` so losing races never reject), and pre-captured-stack rethrow. Adapt defaults/config path and the takeover flag to your host's extension points. Omit chai-flag specifics if your assertion library has native context.
