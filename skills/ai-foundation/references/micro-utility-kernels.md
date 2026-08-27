<!-- capsule-v2 -->
# Micro-utility kernels — which five tiny contracts carry disproportionate invariants a porter would silently get wrong?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What are the exact semantics of SerialJobExecutor, setAbortTimeout, mergeObjects, simulateReadableStream, and handleFetchError?

## SerialJobExecutor — queue drain with shift-after-await
**Path/Symbol:** `packages/ai/src/util/serial-job-executor.ts:SerialJobExecutor` (:3-36, whole file).
**Signature:** `run(job: Job): Promise<void>` resolving/rejecting with the job's own outcome.
**Data Shape:** `queue: Array<Job>`, `isProcessing` latch; jobs are wrapped thunks that resolve/reject the OUTER promise.

### Decisive source
```ts
private async processQueue() {
  if (this.isProcessing) return;
  this.isProcessing = true;
  while (this.queue.length > 0) {
    await this.queue[0]();      // await FIRST…
    this.queue.shift();         // …shift AFTER — job stays at [0] while running
  }
  this.isProcessing = false;
}
```
**Flow:** enqueue wrapper → fire-and-forget `processQueue()` → single drain loop.
**Invariant:** Shift happens AFTER the awaited job completes (peek-run-shift, never enqueue-shift), so re-entrant `run()` calls during a job append without racing the index. A rejected job still leaves the queue consistent and starts the next.
**Probe:** `packages/ai/src/util/serial-job-executor.test.ts:59` (one at a time), `:120` (concurrent run() calls serialize).

## setAbortTimeout — DOMException parity with AbortSignal.timeout
**Path/Symbol:** `packages/ai/src/util/set-abort-timeout.ts:setAbortTimeout` (:14-37).
**Signature:** `setAbortTimeout({abortController?, label, timeoutMs?}): ReturnType<typeof setTimeout> | undefined`.
**Data Shape:** Returns undefined (NO timer) when either controller or timeoutMs is undefined — callers must treat that as "no timeout", not zero.

### Decisive source
```ts
return setTimeout(() => abortController.abort(
  new DOMException(`${label} timeout of ${timeoutMs}ms exceeded`, 'TimeoutError'),
), timeoutMs);
```
**Flow:** guard → schedule abort with labeled TimeoutError reason.
**Invariant:** The abort reason is EXACTLY what `AbortSignal.timeout(ms)` produces (`TimeoutError` DOMException + message naming label and duration) so downstream error classification can't tell manual timers from platform ones; clearable via the returned id.
**Probe:** `packages/ai/src/util/set-abort-timeout.test.ts:31` (TimeoutError DOMException), `:43` (label+duration in message), `:68/:78` (undefined ⇒ no timer).

## mergeObjects — deep merge with prototype-pollution skip
**Path/Symbol:** `packages/ai/src/util/merge-objects.ts:mergeObjects` (:14+, whole file ~80L).
**Signature:** `mergeObjects<T,U>(base?: T, overrides?: U): (T & U) | T | U | undefined` — both undefined ⇒ undefined; one undefined ⇒ the other (identity return).
**Data Shape:** New object result (inputs never mutated); arrays replaced NOT merged; Date/RegExp treated as leaf values.

### Decisive source
```ts
for (const key in overrides) {
  if (key === '__proto__' || key === 'constructor' || key === 'prototype') continue; // pollution guard
  if (Object.prototype.hasOwnProperty.call(overrides, key)) {
    const overridesValue = overrides[key];
    if (overridesValue === undefined) continue;   // explicit undefined NEVER overrides
    // recurse only for plain-ish objects (not Array/Date/RegExp/null)
```
**Flow:** identity fast paths → shallow copy base → recursive per-key override.
**Invariant:** Undefined override values do not erase base values (providerOptions merging depends on this); the three dangerous keys are skipped BEFORE any hasOwnProperty work; arrays and exotic objects replace wholesale.
**Probe:** `packages/ai/src/util/merge-objects.test.ts` (undefined-preserve + pollution-skip pins); consumer pin `stream-text.ts` stepProviderOptions merge.

## simulateReadableStream — pull-based replay with null-vs-zero delay split
**Path/Symbol:** `packages/ai/src/util/simulate-readable-stream.ts:simulateReadableStream` (:12-39).
**Signature:** `simulateReadableStream<T>({chunks: T[], initialDelayInMs? = 0, chunkDelayInMs? = 0, _internal?: {delay?}}): ReadableStream<T>`.
**Data Shape:** `_internal.delay` injection replaces the sleep function for tests (zero-clock suites).

### Decisive source
```ts
return new ReadableStream({ async pull(controller) {
  if (index < chunks.length) {
    await delay(index === 0 ? initialDelayInMs : chunkDelayInMs);
    controller.enqueue(chunks[index++]);
  } else { controller.close(); }
} });
```
**Flow:** pull-driven emission; delays apply per pull.
**Invariant:** `null` delay SKIPS the await entirely while `0` still awaits a zero-ms tick — tests rely on this to distinguish "no backpressure" from "fast backpressure". Work happens in `pull`, so a cancelled stream simply stops pulling (no orphan timers).
**Probe:** `packages/ai/src/util/simulate-readable-stream.test.ts:60` (both null = no delays), `:73/:86` (single-null asymmetry), `:36` (empty array closes immediately).

## handleFetchError — network-error normalization ladder
**Path/Symbol:** `packages/provider-utils/src/handle-fetch-error.ts:handleFetchError` (:29-72).
**Signature:** `handleFetchError({error: unknown, url, requestBodyValues}): unknown` — returns the (possibly same) error.
**Data Shape:** Recognizes `TypeError('fetch failed'|'failed to fetch')` (undici/Browser), Bun-specific codes (`ConnectionRefused, ConnectionClosed, FailedToOpenSocket, ECONNRESET, ECONNREFUSED, ETIMEDOUT, EPIPE`), and aborts.

### Decisive source
```ts
if (isAbortError(error)) return error;                       // aborts pass through untouched
if (error instanceof TypeError &&
    FETCH_FAILED_ERROR_MESSAGES.includes(error.message.toLowerCase())) {
  const cause = (error as any).cause;
  if (cause != null) return new APICallError({
    message: `Cannot connect to API: ${cause.message}`, cause,
    url, requestBodyValues, isRetryable: true });            // network errors ARE retryable
}
if (isBunNetworkError(error)) return new APICallError({ /* same shape */ });
return error;                                                 // anything else: unchanged
```
**Flow:** abort passthrough → fetch-failed unwrap via `.cause` → Bun code check → identity.
**Invariant:** Only CONNECTIVITY failures become retryable APICallErrors; unknown errors pass through UNWRAPPED rather than being coerced (wrongly marking HTTP-level or programming errors retryable is the classic port bug). Cause message is surfaced in `message` for debugging.
**Probe:** exercised through transport verb suites (get-from-api.test.ts network branches); no dedicated unit file at this pin — recorded caveat.

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"SerialJobExecutor setAbortTimeout mergeObjects simulateReadableStream handleFetchError","limit":8}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt all five verbatim — each is dependency-free and its invariant is the entire content (shift-after-await, TimeoutError parity, undefined-preserving deep merge, null-vs-zero delay, connectivity-only retryability). Omit none: these are the load-bearing pebbles under the orchestrator capsules.
