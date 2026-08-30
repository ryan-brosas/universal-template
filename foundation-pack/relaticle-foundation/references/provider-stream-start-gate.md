<!-- capsule-v2 -->
# Provider stream-start gate — how does a retry storm yield fairly without taking chat down when Redis is unavailable?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5dcc97765fcba6fdf62585c541e1b`; direct source/test read (Codebase Memory MCP unavailable this session). **Question:** How should a queued chat turn admit a provider stream without blocking and without coupling Redis failure to assistant availability?

## Non-blocking per-provider token gate with fail-open infrastructure fallback
**Path/Symbol:** `packages/Chat/src/Support/ProviderRateGate.php:tryAcquire` (:17-35); `packages/Chat/src/Jobs/ProcessChatMessage.php:handle` (:158-182); `packages/Chat/config/chat.php:provider_starts_per_second` (:76-84).
**Signature:** `tryAcquire(?string $provider): bool`.
**Data Shape:** Provider names are converted to Redis throttle keys `chat:provider:{provider}`; null uses `default`. The configured rate is cast to an integer and clamped to at least 1. Redis is asked for `allow($limit)->every(1)->block(0)`. A slot returns true, no slot returns false, a `LimiterTimeoutException` returns false, and any other `Throwable` returns true. The queue job releases itself with random 1–4 second jitter when false.

### Decisive source
```php
return (bool) Redis::throttle('chat:provider:'.($provider ?? 'default'))
    ->allow($limit)
    ->every(1)
    ->block(0)
    ->then(static fn (): bool => true, static fn (): bool => false);
```
```php
if (! ProviderRateGate::tryAcquire($this->resolved['provider'])) {
    ChatTelemetry::breadcrumb('stream.provider_gate_release', ['attempt' => $this->attempts()]);
    $this->releaseAuth();
    $this->release(random_int(1, 4));
    return;
}
```

**Flow:** Before opening the provider stream, the job asks a one-second, provider-keyed throttle for a slot without waiting. A denied slot is not treated as a provider error: auth is released, a breadcrumb records the deferral, and the job is requeued with short jitter so many turns do not retry on the same instant. A Redis limiter timeout is also a denial. Other Redis/infrastructure failures fail open, allowing chat to continue rather than making the limiter a hard dependency. Only after admission does `ProcessChatMessage` call `agent->stream(...)`.
**Invariant:** The gate bounds stream starts independently per provider and never holds a worker waiting for capacity. A denied turn must not start a doomed stream; a limiter outage must not make all chat unavailable. The limiter's fail-open branch is intentionally narrower than provider overload handling: provider errors still follow the job's typed retry taxonomy after a stream starts.
**Probe:** `tests/Feature/Chat/ProviderStreamErrorTest.php` (:9-27) pins the adjacent post-admission provider-error classification; `tests/Feature/Chat/StreamRetryBroadcastTest.php` (:8-37) pins immediate retry-progress broadcast shape. No direct Redis-gate test exists in the inspected checkout; `tests/Arch/ArchTest.php` (:184-200) records the class's current grandfathered architecture exception. This coverage gap and the missing live Pest runner are explicit limitations.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "ProviderRateGate tryAcquire provider_gate_release release random_int", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt a non-blocking, provider-partitioned start gate with jittered queue deferral and fail-open behavior for limiter infrastructure faults. Adapt Redis throttle primitives, queue release/auth ownership, and telemetry to the host. Add a direct fake-limiter test in a port to preserve the timeout-versus-infrastructure distinction; this source has no such test in the inspected checkout.
