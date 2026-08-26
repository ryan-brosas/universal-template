<!-- capsule-v2 -->
# Sentinel error taxonomy — which failure degrades a proxy vs retries an engine vs maps to which HTTP status?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How are captcha/block/rate-limit/parser/proxy failures distinguished so policy layers can act without string matching?

## The sentinel set and its three predicates
**Path/Symbol:** `core/common.go:L26–104`, `core/resilient.go:IsProxyChallengeError/shouldRecordCircuitFailure` (L271–284), `core/server.go:mapSearchError` (L454–486).
**Signature:** `IsProxyNetworkError(err) bool`; `classifyProxyNetworkError(err) error`; `IsProxyChallengeError(err) bool`; `shouldRecordCircuitFailure(err) bool`.
**Data Shape:** sentinels: ErrCaptcha, ErrSearchTimeout, ErrParser, ErrEngineInternal, ErrProxyConnect, ErrProxyAuth, ErrTimeout, ErrEmptyResult, ErrBlocked, ErrRateLimited (+ErrProxyUnavailable, ErrCircuitOpen, ErrAllEnginesFailed defined in proxy.go/resilient.go/circuit_breaker.go).

### Decisive source
```go
// common.go — only network-level faults indicate a faulty proxy:
func IsProxyNetworkError(err error) bool {
	return errors.Is(err, ErrProxyConnect) || errors.Is(err, ErrProxyAuth) || errors.Is(err, ErrTimeout)
}
// resilient.go — IP-reputation problems another proxy might dodge:
func IsProxyChallengeError(err error) bool {
	return errors.Is(err, ErrCaptcha) || errors.Is(err, ErrBlocked) || errors.Is(err, ErrRateLimited)
}
// server.go — client-facing mapping (excerpt):
case errors.Is(err, ErrCaptcha):      {status: 429, code: "captcha_detected"}
case errors.Is(err, ErrBlocked):      {status: 403, code: "blocked"}
case errors.Is(err, ErrRateLimited):  {status: 429, code: "blocked"} // meta.upstream_status=429
case errors.Is(err, ErrProxyConnect|ErrProxyAuth|ErrTimeout|ErrProxyUnavailable): {status: 503, ...}
case errors.Is(err, ErrParser|ErrEngineInternal|ErrAllEnginesFailed): {status: 502, ...}
```

**Flow:** transport errors are wrapped by `classifyProxyNetworkError` (matches "407"/"proxy authentication"→ErrProxyAuth; net.Error timeout/deadline/"timeout"→ErrTimeout; "connection refused/reset", "proxyconnect", "no such host", socks…→ErrProxyConnect) preserving the original with `%w: %w`. Captcha/block/429 come from page classification or `ClassifySearchHTTPStatus` (403/401→ErrBlocked, 429→ErrRateLimited, ≥500→ErrBlocked, other non-2xx→ErrParser).
**Invariant:** parser drift, captchas, and engine errors must NEVER degrade proxy health (only IsProxyNetworkError feeds ReportFailure); context cancellation is recorded neither as circuit failure nor retryable error. Every layer branches with `errors.Is`, never substring checks on sentinel names.
**Probe:** `go test ./core -run 'TestRetryableSearch_(Captcha|Parser)NotRetried'` + `core/server_test.go` error-mapping tests.
**Probe executed (real runner):** same command at pin = **2 PASS** (captcha + parser stop at one call); sibling classify suites (TestClassifySearchHTTPStatus/TestSearchError*) green inside the fully green `./core` package run.
**Python-equivalent probe (executed):**
```bash
grep -c 'errors.Is' core/server.go core/resilient.go core/common.go   # → 17/12/8: errors.Is-driven branching confirmed
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "ErrCaptcha ErrProxyConnect classifyProxyNetworkError mapSearchError", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the sentinel set and the three predicates verbatim — they encode the whole ops policy (retry? rotate proxy? trip breaker? return 4xx/5xx?); adapt the HTTP status codes to your framework's conventions; omit the exact regex strings for transport-error classification if your HTTP client surfaces typed errors instead.
