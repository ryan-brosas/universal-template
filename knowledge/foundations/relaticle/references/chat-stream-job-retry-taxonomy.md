<!-- capsule-v2 -->
# Streaming chat job — release-vs-fail-fast retry taxonomy and cancel polling

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** How should a queued LLM-streaming job retry provider errors, honor cancellation mid-stream, and never double-charge?

## ProcessChatMessage handle() + middleware
**Path/Symbol:** `packages/Chat/src/Jobs/ProcessChatMessage.php` (whole, 718L): attributes (:47-55), `middleware()` (:93-100), `handle()` (:102-282), `retryDelaySeconds()` (:284-293), `isRateLimited()` (:300-308), `ProviderRateGate` (support/, 40L).
**Signature:** `#[Timeout(120)] #[MaxExceptions(1)]`; `retryUntil(): now()->addMinutes(3)`; `middleware(): [new WithoutOverlapping($this->conversationId)->releaseAfter(5)->expireAfter(150)]`.
**Data Shape:** Retryable set: `RateLimitedException`, `ProviderOverloadedException`, raw `RequestException` with status ∈ {429, 529, 503}. Delay: `max(min(2**attempts,30), min(Retry-After,60)) + random_int(0,3)`, cap 5 retries.

### Decisive source
```php
// Rate-limit / overloaded errors are transient -> release with backoff.
// release() does not count against MaxExceptions(1); attempts() increments
// each retry. Bounded by this cap AND the job's retryUntil() (now+3min).
// Anything else rethrows and fails fast, exactly as before.
if ($this->isRateLimited($e) && $this->attempts() < self::MAX_RATE_LIMIT_RETRIES) {
    ...
    $this->release($delay); return;
}
throw $e;
```
Cancellation is a cache-pull sentinel INSIDE the event loop: `$cancelled = Cache::pull("chat:cancel:{id}") !== null;` then remaining events are drained but not broadcast, and credits settle at the reserved minimum with reason 'cancelled'. Provider gate: Redis throttle 8 starts/sec/provider with `block(0)` — full limiter ⇒ release with jitter; ANY Redis throwable fails OPEN ("Redis hiccup must never take chat down").

**Flow:** team refresh → paused-workspace early-out WITH reservation refund → bind web-guard user → supersede stale proposals → agent assembly → rate-gate acquire (fail = release 1-4s) → stream events broadcast until cancel sentinel or Error event (converted via ProviderStreamError::toException) → success settles real token cost against the reservation; failure path classifies transient vs fatal.
**Invariant:** Lock contention must NOT consume MaxExceptions (release-after ≠ failure); the auth guard must be forgotten in `finally`; a cancelled stream pays for work received but never re-broadcasts after the sentinel.
**Probe:** `tests/Feature/Chat/TurnSerializationTest.php`, `StreamRetryBroadcastTest.php`, `ChatRateLimitTest.php`, `ChatCancellationTest.php`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ProcessChatMessage handle isRateLimited retryDelaySeconds ProviderRateGate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-lane retry taxonomy (release-with-backoff for transient provider states, fail-fast otherwise), cache-sentinel cancellation inside the stream loop, and fail-open infrastructure gates. Adapt the exception classes to your AI SDK. Omit Laravel Ai specifics. Dedicated suites cover serialization, retries, and cancellation.
