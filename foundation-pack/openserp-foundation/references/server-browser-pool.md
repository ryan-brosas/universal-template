<!-- capsule-v2 -->
# Browser pool (server) — how does the serve process keep one Chrome per authenticated proxy without leaking processes?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** When is a dedicated Chrome launched vs the shared "direct" one, and how are idle/LRU evictions done safely?

## browserPool in cmd layer
**Path/Symbol:** `cmd/serve.go:newBrowserPool/browserPoolKey/browserLaunchURL/get/evictLRULocked/sweepIdle/closePooledBrowser` (L280–470), `pooledBrowserEngine` wrapper (L534–593).
**Signature:** `(p *browserPool) get(requestProxyURL string) (*core.Browser, error)`; `browserPoolKey(url) string`.
**Data Shape:** maxProcesses default 4; key = scheme|host|username|sha16(full userinfo) for authenticated http(s); everything else ⇒ shared "direct" Chrome; idleTTL sweeper ticks idleTTL/4 (≥1s).

### Decisive source
```go
// Hash the full userinfo so a rotating password gets its own Chrome without
// leaking credentials into the key. Scheme+host+username stay readable.
sum := sha256.Sum256([]byte(parsed.User.String()))
return fmt.Sprintf("%s|%s|%s|%s", parsed.Scheme, parsed.Host,
	parsed.User.Username(), hex.EncodeToString(sum[:])[:16])
// SOCKS / unauthenticated / empty ⇒ direct (per-context proxy handles those):
if parsed.Scheme != "http" && parsed.Scheme != "https" { return directBrowserKey }
...
entry := p.browsers[oldestKey]; delete(...); go closePooledBrowser(entry, "lru")
// sweepIdle closes entries idle > idleTTL from a ticker goroutine; close runs
// OUTSIDE the lock via goroutine so eviction never blocks live scrapes.
```
pooledBrowserEngine resolves the engine lazily per request: get(q.ProxyURL) → engine factory(core.Browser, options) → Search/SearchImage; also implements DropProxyLaneCookies, ProxyLaneStats, BrowserPoolStats so the resilient layer can drop lane cookies and report stats through interfaces (proxyLaneCookieDropper/statser in resilient.go). rawEngine serves raw mode for google/yandex/baidu/ecosia with GetRateLimiter returning nil-safe limiter.
**Invariant:** pre-bound launchProxyURL entries survive browser==nil (legacy global proxy warms the pool at startup); LRU eviction count reported as EvictedLRU in BrowserPoolStats (`/stats/proxy` → browser_processes); closing never happens while holding p.mu.
**Probe:** `go test ./cmd -run TestServe` (serve_test.go covers pool key derivation and stats plumbing); live behavior tag-gated.
**Probe executed (real runner):** `-run TestServe` matches zero names — repaired: `go test ./cmd -run TestBrowserPoolKey` = **1 PASS** (scheme|host|user|sha16(userinfo) derivation incl. global-proxy-doesn't-occupy-direct-slot); pool LRU/eviction/stats pinned by TestBrowserPoolEvictLRU/TestLaneStore* in serve_test.go inside the green ./cmd run.
**Python-equivalent probe (executed):**
```bash
grep -n 'directBrowserKey\|go closePooledBrowser\|sweepIdle' cmd/serve.go | head -8
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "browserPool browserPoolKey pooledBrowserEngine sweepIdle BrowserResolver", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt identity-hashed per-proxy Chrome pooling with out-of-lock async close; tune maxProcesses/idleTTL to your RAM; omit the pool if single-proxy (launch one browser directly like the CLI does).
