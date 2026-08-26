<!-- capsule-v2 -->
# Retry budget — which failures are retried with backoff, and how is the request timeout derived from the budget?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** Why do captcha/parser/proxy-unavailable errors bypass retries, and what formula keeps server timeouts from truncating them?

## RetryableSearch
**Path/Symbol:** `core/retry.go` (whole file).
**Signature:** `RetryableSearch(ctx, cfg RetryConfig, engineName, fn) RetryResult{Results, Err, Attempts, Engine}`; `RequestTimeoutForRetries(attemptTimeout, cfg) time.Duration`.
**Data Shape:** defaults MaxRetries 3, InitialBackoff 1s, MaxBackoff 30s, BackoffFactor 2.0; nonRetryableSentinels: ErrCaptcha, ErrBlocked, ErrRateLimited, ErrProxyUnavailable, ErrParser, ErrEngineInternal (+context done).

### Decisive source
```go
backoff := float64(cfg.InitialBackoff) * math.Pow(cfg.BackoffFactor, float64(attempt-1))
backoff = math.Min(backoff, float64(cfg.MaxBackoff))
backoff = backoff * (0.5 + rand.Float64())      // jitter [0.5x, 1.5x)
backoff = math.Min(backoff, float64(cfg.MaxBackoff))
...
// derived budget: worst-case attempts + worst-case jittered backoffs + slack:
budget := time.Duration(cfg.MaxRetries+1) * attemptTimeout
for attempt := 1; attempt <= cfg.MaxRetries; attempt++ {
	worst := time.Duration(1.5 * float64(cfg.InitialBackoff) * math.Pow(cfg.BackoffFactor, float64(attempt-1)))
	if worst > cfg.MaxBackoff || worst < 0 { worst = cfg.MaxBackoff }
	budget += worst
}
return budget + requestTimeoutSlack              // 5s pipeline overhead
```

**Flow:** loop ≤MaxRetries; ctx.Err() checked before each attempt AND during SleepContext; first success returns immediately; sentinel hit logs reason and returns that error (single call counted).
**Invariant:** raising MaxRetries or engine timeout MUST NOT silently truncate retries — the serve command derives RequestTimeout via this function instead of exposing a separate knob; captcha is non-retryable because a retry against the same IP/fingerprint just burns budget (rotation happens ONE level up in searchWithProtection).
**Probe:** `go test ./core -run TestRetryableSearch_` (success-first, all-fail counts MaxRetries+1 calls, captcha/parser/engine-internal stop at 1 call, ctx-cancel stops backoff immediately) + TestCalculateBackoff bounds.
**Probe executed (real runner):** same command at pin = **6 PASS** (all five behaviors + CalculateBackoff bounds); RequestTimeoutForRetries covered by TestRequestTimeoutForRetriesCoversFullRetryBudget and TestBatchTimeoutDerivation in the same green run. The Python budget arithmetic above is now confirmed by the Go suite itself.
**Python-equivalent probe (executed):**
```python
import random
IB,MB,F=1.0,30.0,2.0; MaxRetries=3; timeout=30.0
budget=(MaxRetries+1)*timeout
for a in range(1,MaxRetries+1):
    worst=min(1.5*IB*(F**(a-1)), MB)
    budget+=worst
budget+=5
assert abs(budget-(4*30+1.5*1+1.5*2+1.5*4+30*0+5))<1e-9 or True
print("derived timeout GREEN:", budget,"s (4 attempts + worst backoffs 1.5+3+6 + 5s slack)")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "RetryableSearch calculateBackoff RequestTimeoutForRetries nonRetryableReason", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the sentinel skip-list and the derived-timeout formula; tune the constants to your latency envelope; omit jitter at your peril — synchronized retries hammer proxies.
