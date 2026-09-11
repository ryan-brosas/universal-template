<!-- capsule-v2 -->
# Serial batch uploader machine — how do you serialize fire-and-forget writers onto one HTTP POST slot with infinite retry, server-hinted backoff, and honest close?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What is the exact retry/backoff/close algebra of a ≤1-in-flight batched uploader whose send() failures may be permanent, retryable, or server-scheduled?

## Single-flight drain with resolver-fenced waiting
**Path/Symbol:** `src/cli/transports/SerialBatchEventUploader.ts`: `RetryableError` (:26-33), `enqueue`/:101-119, `flush`/:125-133, `close`/:139-150, `drain`/:156-202, `retryDelay`/:235-253.
**Signature:** config `{ maxBatchSize, maxQueueSize, send(batch)=>Promise<void>, baseDelayMs, maxDelayMs, jitterMs, maxConsecutiveFailures?, onBatchDropped? }`; `RetryableError(message, retryAfterMs?)`.
**Data Shape:** pending:T[]; draining/closed flags; THREE waiter lists — backpressureResolvers (enqueue blocked on maxQueueSize), flushResolvers (queue-empty notification), single sleepResolve (cancellable backoff sleep); droppedBatches counter; pendingAtClose frozen for post-close diagnostics.

### Decisive source
```ts
// failure path inside drain(): re-queue at FRONT, then wait
failures++
if (maxConsecutiveFailures !== undefined && failures >= maxConsecutiveFailures) {
  this.droppedBatches++; this.config.onBatchDropped?.(batch.length, failures)
  failures = 0; this.releaseBackpressure(); continue   // fresh budget per batch
}
// concat (single allocation) instead of unshift(...batch) which shifts
// every pending item batch.length times. Only hit on failure path.
this.pending = batch.concat(this.pending)
const retryAfterMs = err instanceof RetryableError ? err.retryAfterMs : undefined
await this.sleep(this.retryDelay(failures, retryAfterMs))
```
```ts
// retryDelay: server hint overrides exponential for ONE attempt,
// clamped to [baseDelayMs, maxDelayMs] then jittered — a misbehaving
// server can neither hot-loop nor stall the client, and many sessions
// sharing one rate limit don't pounce on the same instant.
const clamped = Math.max(base, Math.min(retryAfterMs, max)); return clamped + jitter
```

**Flow:** enqueue → backpressure wait while full → push + kick drain; drain (guarded by `draining`) takes batches serially until empty/closed; success resets failures; failure re-queues front + sleeps; close() clears pending, wakes ALL waiters (sleep/backpressure/flush), freezes pendingCount.
**Invariant:** At most one drain loop and one in-flight send ever. flush() resolves normally EVEN WHEN batches were dropped ⇒ callers must snapshot droppedBatchCount before/after to detect silent loss. maxConsecutiveFailures budget is PER BATCH, not global. close() must resolve blocked enqueue()s or writers deadlock forever.
**Probe:** `grep -n "export class RetryableError" src/cli/transports/SerialBatchEventUploader.ts` (`:26`), `grep -n "batch.concat(this.pending)" src/cli/transports/SerialBatchEventUploader.ts` (`:184`), `grep -n "backpressureResolvers.push(resolve)" src/cli/transports/SerialBatchEventUploader.ts` (`:112`), `grep -n "pendingAtClose = this.pending.length" src/cli/transports/SerialBatchEventUploader.ts` (`:142`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "SerialBatchEventUploader drain retry backpressure close", limit: 5 });
```

## Verdict
Adopt the whole machine verbatim (it is deliberately generic — caller owns payload via send()). Adapt delays to your SLO. Omit RetryableError only if your server never sends Retry-After semantics.
