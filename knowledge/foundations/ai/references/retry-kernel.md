<!-- capsule-v2 -->
# Provider-utils retry kernel — how do you retry failed LLM calls with backoff while honoring server rate-limit headers without retrying the unrepeatable?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What is the exact attempt/delay/error-wrapping state machine, and how does the repo layer header-aware policy on top of the generic kernel?

## Generic kernel (provider-utils)
**Path/Symbol:** `packages/provider-utils/src/retry-with-exponential-backoff.ts:retryWithExponentialBackoff` (:36–63 factory, internal recursion :65–143).
**Signature:** `({maxRetries=2, initialDelayInMs=2000, backoffFactor=2, abortSignal?, shouldRetry, getDelayInMs?, createRetryError?}) => RetryFunction` where `RetryFunction = <OUTPUT>(fn: () => PromiseLike<OUTPUT>) => PromiseLike<OUTPUT>`.
**Data Shape:** `RetryErrorReason = 'maxRetriesExceeded' | 'errorNotRetryable'`; error list accumulates across attempts and is carried in every wrapped error.

### Decisive source
```ts
try {
  return await f();
} catch (error) {
  if (isAbortError(error)) {
    throw error; // don't retry when the request was aborted
  }
  if (maxRetries === 0) {
    throw error; // don't wrap the error when retries are disabled
  }
  ...
  const newErrors = [...errors, error];
  const tryNumber = newErrors.length;
  if (tryNumber > maxRetries) {
    throw createRetryError({
      message: `Failed after ${tryNumber} attempts. Last error: ${errorMessage}`,
      reason: 'maxRetriesExceeded',
      errors: newErrors,
    });
  }
  if ((await shouldRetry(error)) && tryNumber <= maxRetries) {
    await delay(getDelayInMs({ error, exponentialBackoffDelay: delayInMs }), { abortSignal });
    return retryWithExponentialBackoffInternal(f, { ..., delayInMs: backoffFactor * delayInMs }, newErrors);
  }
  if (tryNumber === 1) {
    throw error; // don't wrap the error when a non-retryable error occurs on the first try
  }
  throw createRetryError({ message: `Failed after ${tryNumber} attempts with non-retryable error: ...`, reason: 'errorNotRetryable', errors: newErrors });
}
```
(retry-with-exponential-backoff.ts:86–142, verbatim)

**Flow:** invoke → abort ⇒ rethrow raw → maxRetries=0 ⇒ rethrow raw (never wrapped) → attempts exhausted ⇒ wrap as `maxRetriesExceeded` → shouldRetry says yes ⇒ delay (`getDelayInMs`, default exponential) then recurse with doubled base delay → non-retryable on FIRST try ⇒ rethrow raw; on a later try ⇒ wrap as `errorNotRetryable`.
**Invariant:** (1) AbortErrors are NEVER retried NOR wrapped — cancellation must stay instantaneous and identity-preserved. (2) The original error surfaces unwrapped whenever no retry happened (first-attempt refusal or disabled retries); wrapping only accumulates context that actually accrued. (3) Delay growth is multiplicative on `delayInMs`, not computed from tryNumber — a custom `getDelayInMs` receives the CURRENT base.
**Probe:** kernel behavior pinned through the wrapper's suites — `ai/src/util/retry-with-exponential-backoff.test.ts:88` (falls back to exponential when rate-limit delay too long), `:125` (no headers), `:286` (backoff progression), `:414` (negative header value rejected).

## Header-respecting wrapper + wiring
**Path/Symbol:** `packages/ai/src/util/retry-with-exponential-backoff.ts:getRetryDelayInMs` (:9–78) + `retryWithExponentialBackoffRespectingRetryHeaders` (:80–98); wired via `packages/ai/src/util/prepare-retries.ts:prepareRetries` (:7–44) into generateText/streamText step calls.
**Data Shape:** reads `responseHeaders['retry-after-ms']` (float ms) then `'retry-after'` (seconds OR HTTP-date parsed to ms delta); sanity gate `0 <= ms < 60_000 || ms < exponentialBackoffDelay` else fall back to exponential; also digs `error.cause` APICallError headers.
**Flow:** prepareRetries validates integer ≥0 (`InvalidArgumentError` otherwise), defaults 2, binds abortSignal once per run → each step call wraps `streamLanguageModelCall(...)` in `retry(...)`.
**Invariant:** server-provided delays REPLACE backoff only within the sanity window — an infinite/huge `retry-after` can never wedge a client forever. `shouldRetry` admits only `isRetryable === true` APICall/Gateway errors; everything else fails fast.
**Probe:** `retry-with-exponential-backoff.test.ts:19` (ms header honored at fake-timer precision), `:340` (ms preferred over s), `:372` (HTTP-date), `:524` (cause-chain headers), `:453/:482/:510` (Gateway retryability).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "retryWithExponentialBackoff getRetryDelayInMs retry-after", limit: 10 });
```

## Verdict
Adopt the four-outcome state machine (abort / disabled / exhausted / retry-or-fail), accumulated-error wrapping with raw rethrow when nothing accrued, and the header-delay sanity window. Adapt defaults (2 retries, 2s, ×2) and retryability predicate to host error taxonomy. Omit Gateway-specific error classes if your host has none. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2; decisive ranges read at HEAD this session.
