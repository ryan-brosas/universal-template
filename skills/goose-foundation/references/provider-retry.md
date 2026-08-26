<!-- capsule-v2 -->
# Provider retry/backoff ladder — exponential backoff with jitter, transient-only gating, permanent-failure markers, and a one-shot auth-refresh retry

**Source:** goose Apache-2.0 `main@2eb3ab1001dedb5ab09a6ed60158adfc248bac56`; Codebase Memory `goose`. **Question:** how to build a provider-call retry wrapper that retries only transient errors with capped exponential backoff plus jitter, honors a provider-supplied `retry_delay` for rate limits, treats specific Anthropic `thinking`-block 400s as permanently unretryable, and performs at most one independent credential refresh on auth errors?

## RetryConfig and retry_operation
**Path/Symbol:** `crates/goose-provider-types/src/retry.rs:RetryConfig` (struct), `RetryConfig::delay_for_attempt` (65-81), `should_retry` (100-109), `retry_operation` (111-150), `ProviderRetry` trait (156-179), blanket impl `P::with_retry_config` (187-260).
**Signature:** `RetryConfig { max_retries: usize, initial_interval_ms: u64, backoff_multiplier: f64, max_interval_ms: u64, transient_only: bool }`; `fn delay_for_attempt(&self, attempt: usize) -> Duration`; `fn should_retry(error: &ProviderError, config: &RetryConfig) -> bool`; `async fn retry_operation<F,Fut,T>(config: &RetryConfig, operation: F) -> Result<T, ProviderError>`; `async fn with_retry_config<F,Fut,T>(&self, operation: F, config: RetryConfig) -> Result<T, ProviderError>`.
**Data Shape:** defaults `max_retries=3`, `initial_interval_ms=1000`, `backoff_multiplier=2.0`, `max_interval_ms=30000`, `transient_only=false`. `delay_for_attempt(0)` → 0ms; attempt *n* → `min(initial·multiplier^(n-1), max_interval)` then jitter factor `0.8 + rand()*0.4` (thundering-herd avoidance). Retryable classes: `RateLimitExceeded`, `ServerError`, `NetworkError` always; `RequestFailed` only when `!transient_only` unless it matches a permanent marker. Auth errors are never retried by `should_retry`.

### Decisive source
```rust
// retry.rs — capped exponential backoff with jitter; attempt 0 is immediate
pub fn delay_for_attempt(&self, attempt: usize) -> Duration {
    if attempt == 0 { return Duration::from_millis(0); }
    let exponent = (attempt - 1) as u32;
    let base_delay_ms = (self.initial_interval_ms as f64
        * self.backoff_multiplier.powi(exponent as i32)) as u64;
    let capped_delay_ms = std::cmp::min(base_delay_ms, self.max_interval_ms);
    let jitter_factor_to_avoid_thundering_herd = 0.8 + (rand::random::<f64>() * 0.4);
    let jitter_delay_ms = (capped_delay_ms as f64 * jitter_factor_to_avoid_thundering_herd) as u64;
    Duration::from_millis(jitter_delay_ms)
}

// Permanent 400s: Anthropic rejects signed thinking/redacted_thinking blocks as
// immutable once a thinking model's config changes mid-conversation; the identical
// payload is rebuilt on every retry, so retrying can never succeed.
const PERMANENT_REQUEST_FAILURE_MARKERS: &[&str] = &[
    "blocks in the latest assistant message cannot be modified",
    "must remain as they were in the original response",
    "Reasoning is mandatory for this endpoint",
];

pub fn should_retry(error: &ProviderError, config: &RetryConfig) -> bool {
    match error {
        ProviderError::RateLimitExceeded { .. }
        | ProviderError::ServerError(_)
        | ProviderError::NetworkError(_) => true,
        ProviderError::RequestFailed(message) if is_permanent_request_failure(message) => false,
        ProviderError::RequestFailed(_) => !config.transient_only,
        _ => false,
    }
}

// retry_operation: loop, sleep(delay) between attempts; rate-limit errors may
// supply their own retry_delay which overrides the computed backoff.
let delay = match &error {
    ProviderError::RateLimitExceeded { retry_delay: Some(d), .. } => *d,
    _ => config.delay_for_attempt(attempts),
};
sleep(delay).await;
```

**Flow:** `retry_operation` loops: on `Ok` return; on `Err`, if `should_retry && attempts < max_retries`, increment attempts, log, compute delay (rate-limit `retry_delay` overrides computed backoff), `sleep`, continue; otherwise return the error. The blanket `ProviderRetry` impl adds an auth dimension: on `Authentication` error, at most once (independent of `max_retries`) it calls `self.refresh_credentials().await` and on success `continue`s; on refresh failure it logs and falls through to the normal retry decision. `GOOSE_PROVIDER_SKIP_BACKOFF` env var (parsed bool, default false) skips the `sleep` for fast tests.
**Invariant:** only transient classes are retried; a provider-supplied rate-limit `retry_delay` wins over the computed backoff; backoff is capped at `max_interval_ms` and jittered to avoid thundering herds; permanent Anthropic `thinking`-block 400s are never retried; auth errors trigger at most one credential refresh independent of the retry budget and are otherwise not retried.
**Probe:** `crates/goose-provider-types/src/retry.rs` `#[cfg(test)]` — 8 tests: `default_config_retries_request_failed`, `never_retries_permanent_thinking_block_400`, `permanent_request_failure_marker_detection`, `transient_only_skips_request_failed`, `transient_only_still_retries_server_error`, `transient_only_still_retries_network_error`, `transient_only_still_retries_rate_limit`, `never_retries_auth_errors`. Verified GREEN via `cargo test -p goose-provider-types --lib retry` (8 passed, 0 failed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "goose", query: "retry_operation should_retry RetryConfig delay_for_attempt ProviderRetry with_retry_config", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the retry/backoff ladder: `RetryConfig` with capped exponential backoff and jitter, `should_retry` gating on transient classes, permanent-failure substring markers, rate-limit `retry_delay` override, and the one-shot independent auth-refresh retry. Adapt the permanent markers to the target provider's own deterministic-400 language and the `GOOSE_PROVIDER_SKIP_BACKOFF` env override to the host's test-injection convention. Omit the `Provider`/`ProviderRetry` trait coupling and `refresh_credentials` plumbing when porting to a non-OAuth provider. Coverage: `crates/goose-provider-types/src/retry.rs` `no_recorded_issue` + `metadata_match`; the cargo test runner is available in this checkout and the module's 8 direct tests pass.
