<!-- capsule-v2 -->
# Resilient pipeline — how do limiter, circuit breaker, proxy policy, and panic recovery compose around one engine call?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What is the exact order of protections for a single search, and when may a challenged proxy be retried once?

## searchWithProtection
**Path/Symbol:** `core/resilient.go:searchWithProtection` (L161–269), `SearchPrimary/SearchWithFallback` (L92–159), `invokeEngine` (L300–315).
**Signature:** `searchWithProtection(ctx, engine, q, isImage) ([]SearchResult, ProxyExecutionMeta, error)`; `RetryableSearch` wraps `runOnce`.
**Data Shape:** ProxyExecutionMeta{mode, tag, used(masked), attempts}.

### Decisive source
```go
cb := rs.cbManager.Get(engine.Name())
if !cb.AllowRequest(engineCtx) { return nil, meta, ErrCircuitOpen }
policy := rs.effectivePolicyForQuery(engine.Name(), q)
runOnce := func() RetryResult { return RetryableSearch(..., func(callCtx) {
	limiter := engine.GetRateLimiter(); if err := limiter.Wait(callCtx); ...   // 1. pace
	switch policy.Mode {
	case Off: attemptQuery.ProxyURL=""
	case RequestURL: proxyURL = q.ProxyURL
	case TagPool: proxyURL = rs.selectProxyForQuery(policy, q, ctx); reportToRegistry = tag != ""
	}
	results, err := invokeEngine(...)          // the ONLY panic-recovery point
	if reportToRegistry { rs.reportProxyAttempt(ctx, proxyURL, err) }        // health: only network errors degrade
	if errors.Is(err, ErrCaptcha) && DropCookiesOnChallenge { dropper.DropProxyLaneCookies(...) }
	return results, err }) }
// ONE challenged-proxy rotation, tag-pool only, needs ≥2 healthy:
canRotateChallengedProxy := result.Err != nil && policy.Mode == TagPool && tag != "" &&
	rs.proxyRegistry != nil && IsProxyChallengeError(result.Err) &&
	rs.proxyRegistry.HealthyCountForTag(tag) >= 2 && ctx.Err() == nil
if canRotateChallengedProxy { ReportChallenged(last); result = runOnce(); attempts = 2 }
```

**Flow:** dedicated endpoints stay engine-pure (SearchPrimary, no fallback) unless AllowEndpointFallback; fallback iterates other initialized engines but returns immediately on ErrProxyUnavailable (policy failed closed ⇒ trying other engines can't help). Mega modes reuse the same per-engine protection in parallel/any/fastest shapes.
**Invariant:** rate-limit Wait errors are normalized back to the caller's context error (normalizeLimiterWaitErr) so an impatient client isn't recorded as an engine failure; cb.RecordSuccessDuration only after full success; attempts>1 only ever from the single sanctioned rotation.
**Probe:** `go test ./core -run 'TestSearchWithProtection|TestResilient|TestFallback'` (proxy_rotation_test.go + resilient_context_test.go).
**Probe executed (real runner):** same command at pin = **9 PASS**: rotation-on-captcha, no-rotation single-proxy/global-challenge/direct-mode fail-fast paths; ResilientSearchPrimary circuit semantics (engine failure opens, ctx errors never open, limiter deadline never opens, cancel stops <100ms), fallback skip-uninitialized.
**Python-equivalent probe (executed):**
```bash
grep -n 'HealthyCountForTag(policy.Tag) >= 2\|invokeEngine(' core/resilient.go | head -3
# → L246 rotation gate; L214/303-314 single recovery point confirmed
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "searchWithProtection SearchWithFallback invokeEngine reportProxyAttempt DropProxyLaneCookies", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the ordering (breaker → policy → limiter → proxy select → recovered call → health report → cookie drop on captcha) and the one-shot rotation gate; adapt fallback breadth to your SLA; omit image plumbing if you serve web only.
