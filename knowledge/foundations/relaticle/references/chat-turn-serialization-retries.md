<!-- capsule-v2 -->
# ProcessChatMessage turn serialization + retry taxonomy — how does one streaming LLM turn per conversation coexist with provider rate limits and a fail-fast error policy?

**Source:** relaticle AGPL-3.0 `main@2c2a2456`; Codebase Memory `relaticle`. **Question:** which failures release-and-retry, which fail immediately, and how is single-writer-per-conversation enforced?

## WithoutOverlapping keying + MaxExceptions(1) + classified releases
**Path/Symbol:** `packages/Chat/src/Jobs/ProcessChatMessage.php` (`middleware` :93-100, constructor :65-78, `handle` catch :257-282, `isRateLimited` :300-308, `retryDelaySeconds` :284-293, `retryUntil` :80-83). Attributes: `#[Timeout(120)] #[MaxExceptions(1)]`, queue `chat`, `$this->afterCommit = true`.
**Signature:** `middleware(): array<int, WithoutOverlapping>` → `new WithoutOverlapping($this->conversationId)->releaseAfter(5)->expireAfter(150)`.
**Data Shape:** retryable set = `RateLimitedException | ProviderOverloadedException | RequestException(429|529|503)`; delay = `max(min(2**attempts, 30), min(Retry-After header, 60))` + jitter `random_int(0, 3)`; hard ceiling `retryUntil() = now()+3min`; rate-retry cap 5.

### Decisive source
```php
/**
 * One streaming turn per conversation at a time. A second turn (new send,
 * continuation, or another tab) is released back to the queue and retried
 * until retryUntil(); a real exception trips maxExceptions=1 and fails fast
 * (no re-stream). Lock contention is not an exception, so it does not count.
 */
public function middleware(): array
{
    return [new WithoutOverlapping($this->conversationId)->releaseAfter(5)->expireAfter(150)];
}
...
if ($this->isRateLimited($e) && $this->attempts() < self::MAX_RATE_LIMIT_RETRIES) {
    // Honor the provider's Retry-After when present; jitter spreads
    // the re-dispatch so concurrent 429ed jobs don't stampede back.
    $delay = $this->retryDelaySeconds($this->attempts(), $e) + random_int(0, 3);
    $this->broadcastSafely(new ChatStreamRetrying(...));
    $this->release($delay);
    return;
}
throw $e;
```

**Flow:** dispatch after commit → queue worker serializes per conversation via the cache lock (contention RELEASES the job — never counts as an exception) → pre-model setup may refund+return quietly → provider gate (`ProviderRateGate::tryAcquire`, Redis throttle fail-open) else `release(random_int(1,4))` → stream; Error events become exceptions via `ProviderStreamError::toException`; cancel checked per event via `Cache::pull`. Transient provider errors release with backoff+jitter and broadcast an attempt counter to the UI; anything else rethrows → `failed()` settles minimum credit, supersedes proposals, backfills a coherent dead turn, broadcasts failure.
**Invariant:** lock contention and provider throttling NEVER consume the single max-exception budget — only genuine stream errors do, and they kill the job on first occurrence (no partial re-stream). All releases are bounded by two independent ceilings (5 attempts / 3 minutes). Auth binding is scoped: `Auth::guard('web')->setUser` at start, `forgetUser()` in finally.
**Probe:** `tests/Feature/Chat/TurnSerializationTest.php:12` (per-conversation serialization), `StreamRetryBroadcastTest.php` (retry broadcast), `ChatRateLimitTest.php`/`ChatSendRateLimitTest.php` (gates), `ProcessChatMessageFailureTest.php` (:55 dead-turn coherence, :104 no duplicate on post-stream failure).
**Coverage caveat:** none beyond standard best-effort.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ProcessChatMessage WithoutOverlapping isRateLimited retryDelaySeconds ProviderRateGate", limit: 8, fields: ["signature", "lines"] });
```

## Verdict
Adopt: the three-way classification (lock contention ⇒ release; transient provider ⇒ bounded backoff release; logic error ⇒ immediate fail) with independent time/attempt ceilings and UI-visible attempt broadcasts. Adapt exception types and gate config to your providers. Omit Laravel\Ai specifics.
