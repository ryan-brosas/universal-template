<!-- capsule-v2 -->
# Raw-HTTP status-to-sentinel gate — which HTTP codes map to blocked vs rate-limited vs parser errors before HTML parsing starts?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How does the raw (non-browser) search path decide, from the HTTP layer alone, that a request is dead?

## Status classification ladder
**Path/Symbol:** `core/http_client.go` — `ClassifySearchHTTPStatus` L209–225, `ReadRawSearchBody` L199–207, `RawSearchRequest` L105–118; consumers `yandex/search_raw.go:44–51`, `baidu/search_raw.go:39–46`.
**Signature:** `ReadRawSearchBody(resp *http.Response) ([]byte, error)` — classifies BEFORE `io.ReadAll(resp.Body)`; `ClassifySearchHTTPStatus(status int) error`.
**Data Shape:** sentinel mapping: 401/403 → `ErrBlocked`; 429 → `ErrRateLimited`; ≥500 → wrapped `ErrBlocked` ("search engine returned HTTP %d"); 0 → nil (transport-level success marker); other non-2xx → wrapped `ErrParser`.

### Decisive source
```go
// core/http_client.go:209-225
func ClassifySearchHTTPStatus(status int) error {
    switch status {
    case 0:                               return nil            // caller-supplied/odd path
    case http.StatusForbidden, http.StatusUnauthorized:
                                          return ErrBlocked     // challenge family
    case http.StatusTooManyRequests:      return ErrRateLimited // limiter/backoff policy
    }
    if status >= 500 { return fmt.Errorf("%w: search engine returned HTTP %d", ErrBlocked, status) }
    if status < 200 || status >= 300 { return fmt.Errorf("%w: ...", ErrParser, status) }
    return nil
}
```
The sentinel choice is load-bearing downstream: retry-budget treats captcha/blocked/429/parser as NON-retryable while proxy-unavailable and transient network errors rotate proxies (see retry-budget capsule); circuit-breaker counts failures by the same taxonomy.
**Flow:** `RawSearchRequest` → profile pick → cached tls-client GET (redirects NOT followed client-side; guarded mode walks them manually validating every hop via `ValidatePublicHTTPURL`, max 10 hops ⇒ wrapped `ErrEngineInternal`) → `DrainAndCloseResponse` defer → body read through this classifier → THEN html classify (`classifyYandexDocument`) can still flag in-band captcha inside a 200 page.
**Invariant:** two independent block detectors run in sequence — HTTP-status gate first (cheap), DOM-classifier second (in-band challenges ship as 200s); a 200 with zero parsed rows becomes wrapped `ErrParser`, never an empty success, UNLESS the DOM classifier said ErrEmptyResult.
**Probe:** `core/http_client_test.go` pins the status table; per-engine raw suites (`yandex/search_raw_test.go:16 TestYandexParseHTMLFixtures`) cover the parse side.
**Python-equivalent probe (executed byte-exact):**
```bash
grep -c 'ErrBlocked\|ErrRateLimited\|ErrParser' core/http_client.go   # → 4 sentinel sites + import refs
```
```python
def classify(status):
    if status == 0: return None
    if status in (401, 403): return "ErrBlocked"
    if status == 429: return "ErrRateLimited"
    if status >= 500: return "ErrBlocked"
    if not (200 <= status < 300): return "ErrParser"
    return None
assert [classify(s) for s in (403,429,503,302,200)] == ["ErrBlocked","ErrRateLimited","ErrBlocked","ErrParser",None]
print("status-gate GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "RawSearchRequest ClassifySearchHTTPStatus ReadRawSearchBody", limit: 4, fields: ["signature","name","file"] });
```
Live at pin: rank-1 `core.RawSearchRequest` http_client.go:105–118; rank-2 `ValidatePublicHTTPURL` network_guard.go:51–57 (total:6).

## Verdict
Adopt the exact status→sentinel table so your retry/proxy/circuit policies key off one taxonomy; keep the two-layer (status then DOM) detection order. Adapt only the wrap messages.
