<!-- capsule-v2 -->
# Retryer pause/resume machine — how does one retry loop serve online/offline + focus pause without losing retries?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How can a single async retry loop pause when the tab hides or the network drops, resume exactly where it stopped, and keep cancel/retry semantics straight — without a state machine library?

## createRetryer closure kernel
**Path/Symbol:** `packages/query-core/src/retryer.ts:createRetryer` (lines 76–237).
**Signature:** `createRetryer<TData, TError>(config: RetryerConfig): Retryer<TData>` where config = `{ fn, initialPromise?, onCancel?, onFail?, onPause?, onContinue?, retry?, retryDelay?, networkMode, canRun }`.
**Data Shape:** closure locals: `isRetryCancelled: boolean`, `failureCount: number`, `continueFn?: (value?) => void`, `status: 'pending'|'resolved'|'rejected'`; one externally exposed `promise` whose handlers are captured at construction and immediately silenced with `promise.catch(noop)`.

### Decisive source
```ts
const pause = () => {
  return new Promise((continueResolve) => {
    continueFn = (value) => {
      if (isResolved() || canContinue()) {
        continueResolve(value)
      }
    }
    config.onPause?.()
  }).then(() => {
    continueFn = undefined
    if (!isResolved()) {
      config.onContinue?.()
    }
  })
}
```
and the failure path of the single recursive loop:
```ts
sleep(delay)
  .then(() => {
    return canContinue() ? undefined : pause()
  })
  .then(() => {
    if (isRetryCancelled) {
      reject(error)
    } else {
      run()
    }
  })
```

**Flow:** run() executes `initialPromise ?? fn()` (initialPromise ONLY when `failureCount === 0`) → on rejection compute shouldRetry (`retry === true || number < retryCount || fn(failureCount,error)`; default `environmentManager.isServer() ? 0 : 3`) → increment failureCount → onFail → sleep(retryDelay) → **if not canContinue(), await pause()** → check isRetryCancelled latch (reject if set) → recurse run(). start() runs immediately if `canStart()` (= `canFetch(networkMode) && canRun()`), else `pause().then(run)`. External `cancel()` rejects once with a CancelledError carrying `{revert?, silent?}` and calls onCancel. `continue()` invokes continueFn; `cancelRetry()`/`continueRetry()` just flip the latch.
**Invariant:** (1) every exit path funnels through resolve/reject which are guarded by `!isResolved()` — double settle is impossible; (2) pause() resolution is GATED: continueFn resolves only `if (isResolved() || canContinue())`, so a stale focus/online blip cannot resume into a still-blocked condition — callers may need to invoke continue() again when conditions actually change; (3) the isRetryCancelled check happens AFTER the pause window, so cancelling retries during backoff kills the attempt without rejecting the original promise mid-sleep.
**Probe:** `packages/query-core/src/__tests__/query.test.tsx` ("should throw a CancelledError when a paused query is cancelled" :152, paused-state assertions :88/:134/:171-173) pins that cancelling while `fetchStatus === 'paused'` rejects and leaves the paused state observable. Also `grep -n "canContinue() ? undefined : pause()" packages/query-core/src/retryer.ts`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^createRetryer$", limit: 3 });
```

## Verdict
Adopt the whole closure kernel verbatim for any host runtime needing retry+pause semantics; it has zero dependencies beyond sleep/timeoutManager. Adapt `canContinue()` inputs (focusManager/onlineManager are injectable globals) and defaultRetryDelay's `min(1000 * 2**failureCount, 30000)` cap to product policy. Omit the deprecated `isCancelledError()` function shim. No direct-runner caveat: upstream tests cited above were not executed this window (no installed workspace deps); behavior verified by deterministic source inspection + graph retrieval instead.
