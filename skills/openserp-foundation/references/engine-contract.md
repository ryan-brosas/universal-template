<!-- capsule-v2 -->
# Engine contract — what must a new engine implement, and how does the pipeline wrap it?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** Which methods and defaults make a struct a pluggable engine, and where do engine panics stop being process-killers?

## SearchEngine interface + options
**Path/Symbol:** `core/server.go:SearchEngine` (L39–52), `core/common.go:SearchEngineOptions` (L496–564).
**Signature:** `Search(ctx, Query) ([]SearchResult, error); SearchImage(ctx, Query) ([]SearchResult, error); IsInitialized() bool; Name() string; GetRateLimiter() *rate.Limiter`.
**Data Shape:** engines embed `core.Browser` (or wrap raw funcs) + `core.SearchEngineOptions`; `Name()` returns the stable route id (`"google"`, `"duckduckgo"` → endpoint alias `duck`). Options default via `Init()`: rate 6 req / 60 s, burst 1, selector timeout 5 s.

### Decisive source
```go
func (o *SearchEngineOptions) GetRateLimiter() *rate.Limiter {
	every := o.GetRatelimit()          // RateTime*Second / RateRequests
	burst := o.RateBurst
	searchEngineOptionsLimiterMu.Lock()
	defer searchEngineOptionsLimiterMu.Unlock()
	if o.limiterState == nil { o.limiterState = &rateLimiterState{} }
	if o.limiterState.limiter == nil || o.limiterState.every != every || o.limiterState.burst != burst {
		o.limiterState.limiter = rate.NewLimiter(rate.Every(every), burst)
		...
	}
	return o.limiterState.limiter
}
```

**Flow:** `New(browser, opts)` → `opts.Init()` → store options + `core.NewEngineLogger(name)` → `Search()` scopes the receiver (`scoped := *gogl; scoped.logger = gogl.logger.WithRequest(ctx); gogl = &scoped`) so per-request logging never mutates the shared engine.
**Invariant:** the limiter state is intentionally SHARED across all requests of one engine — never copy `SearchEngineOptions` after first use; a copied limiter silently removes rate limiting. Panics inside `engine.Search` are converted to `ErrEngineInternal` only at `invokeEngine` (resilient.go L303) — engines need no own recover.
**Probe:** `go test ./core -run TestRateLimiter` (rate_limiter_test.go pins interval/burst); panic conversion pinned by `core/browser_panic_test.go`.
**Probe executed (real runner):** `-run TestRateLimiter` matches zero names — repaired: `TestSearchEngineOptionsGetRateLimiterCachesLimiterAndPaces|TestRetryAppliesRateLimiterOnEachAttempt` = **2 PASS** at pin; panic plane `TestInvokeEngineRecoversPanics|TestRecoverEnginePanic|TestPanickingSearchImageReturns502AndServerSurvives` = **3 PASS**.
**Python-equivalent probe (executed):**
```bash
grep -n 'limiterState' core/common.go | head -3   # → L509/512/550: shared cached state confirmed
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "SearchEngine GetRateLimiter invokeEngine", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the 5-method interface, `Init()` zero-value defaults, and receiver-scoping idiom; adapt the concrete rod/raw execution per host; omit the specific 6req/60s numbers if your upstream tolerances differ. Direct tests pin the limiter and panic path; coverage clean at pin.
