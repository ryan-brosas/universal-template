<!-- capsule-v2 -->
# Deadline poll ladder — how do you poll a flaky predicate until it passes, bounded by one monotonic deadline, and still report the last failure?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** What is the correct shape for retry-polling — backoff intervals, deadline checks, timeout result — such that the caller can render the LAST observed error after a timeout?

## raceAgainstDeadline discriminated union + pollAgainstDeadline shrinking-interval ladder
**Path/Symbol:** `packages/isomorphic/timeoutRunner.ts` (`raceAgainstDeadline` 25-40, `pollAgainstDeadline` 42-62); consumer `packages/playwright/src/matchers/matchers.ts:toPass` (496-530) via `deadlineForMatcher` (547-559).
**Signature:** `raceAgainstDeadline<T>(cb: () => Promise<T>, deadline: number): Promise<{ result: T, timedOut: false } | { timedOut: true }>`; `pollAgainstDeadline<T>(callback: () => Promise<{ continuePolling: boolean, result: T }>, deadline: number, pollIntervals: number[] = [100, 250, 500, 1000]): Promise<{ result?: T, timedOut: boolean }>`.
**Data Shape:** deadline is an absolute MONOTONIC timestamp (0 = no limit); callback returns `{continuePolling, result}` where result carries the last failure; final shape keeps `result?` populated even on `timedOut: true`.

### Decisive source
```ts
export async function pollAgainstDeadline<T>(callback: () => Promise<{ continuePolling: boolean, result: T }>, deadline: number, [...pollIntervals]: number[] = [100, 250, 500, 1000]): Promise<{ result?: T, timedOut: boolean }> {
  const lastPollInterval = pollIntervals.pop() ?? 1000;
  let lastResult: T|undefined;
  const wrappedCallback = () => Promise.resolve().then(callback);
  while (true) {
    const time = monotonicTime();
    if (deadline && time >= deadline)
      break;
    const received = await raceAgainstDeadline(wrappedCallback, deadline);
    if (received.timedOut)
      break;
    lastResult = (received as any).result.result;
    if (!(received as any).result.continuePolling)
      return { result: lastResult, timedOut: false };
    const interval = pollIntervals!.shift() ?? lastPollInterval;
    if (deadline && deadline <= monotonicTime() + interval)
      break;
    await new Promise(x => setTimeout(x, interval));
  }
  return { timedOut: true, result: lastResult };
}
```

**Flow:** each attempt races the callback against the absolute deadline (timer cleared in `.finally`; deliberate `await` before racing preserves async stacks inside cb). Success with `continuePolling:false` returns immediately. Otherwise shift the next interval off the ladder (100→250→500→1000, then repeat 1000 forever) — but break BEFORE sleeping if the interval would overshoot the deadline, so the loop never ends on a pointless sleep. On timeout, `lastResult` — the most recent attempt's failure value — survives into the result so `toPass` can render "Timeout … exceeded while waiting on the predicate" PLUS the real received error and Call Log.
**Invariant:** intervals are CONSUMED (mutated array) — pass a fresh array per call or the ladder is already collapsed; `deadline=0` disables every time check (poll forever); monotonic clock only — wall-clock changes must not extend/shorten polling. File header caveat honored: this module deliberately does NOT use `builtins.setTimeout` and "can break when clock emulation is engaged" — never port it into injected/page context.
**Probe:** repository-owned direct test: `tests/playwright-test/expect-to-pass.spec.ts:19-60` — 'should retry predicate' asserts i reaches exactly 3 (no extra invocations), 'should respect timeout' asserts exit code 1 and output containing `Timeout 100ms exceeded while waiting on the predicate`. Execution BLOCKED standing in this lane (read-only checkout, no node_modules); evidence = byte-exact read of both ranges at pin HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", file_pattern: "*timeoutRunner*", detail: "ids", limit: 10 });
```
(executed live → raceAgainstDeadline :25-40, pollAgainstDeadline :42-62, wrappedCallback; consumers via search_code `pollAgainstDeadline` → matchers.ts toPass :496-530, expect.ts invokePollMatcher :425-464.)

## Verdict
Adopt the discriminated-union race result, the consume-once backoff ladder with the pre-sleep deadline check, and last-result preservation on timeout. Adapt default intervals and where the deadline comes from (Playwright derives it from matcher config + testInfo). Omit the `isNot` polarity flip in `toPass` unless you port expect-style negation (`expect(fn).not.toPass()` polls until it FAILS). Distinct from the client TimeoutSettings precedence ladder (`timeout-settings-ladder`) — that decides WHICH timeout applies; this decides HOW polling behaves under it.
