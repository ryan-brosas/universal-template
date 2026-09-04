<!-- capsule-v2 -->
# Response cache — what belongs in a cache key for market-sensitive SERP responses, and when must caching be skipped?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** Why do proxy requests without market metadata bypass the cache, and what else forces BYPASS?

## Key composition + bypass rules
**Path/Symbol:** `core/cache.go` (whole file), `core/server.go:cacheEnvelopeIfEligible/tryServeCacheHit/refreshCachedMeta/buildMegaCacheKey/megaCacheableEngines` (L569–601, L1333–1477).
**Signature:** `BuildCacheKey(engine, action, q Query) string` (sha256 of pipe-joined fields); `ShouldBypassCacheForProxyMarket(q) bool`.
**Data Shape:** TTL 5m, maxSize 1000 defaults; fields: engine|action|text|lang|region|date|file|site|limit|start|filter|features|proxy_country|proxy_class|proxy_provider (lower-cased/trimmed); mega prefix "mega:{mode}:{merge}:{dedupe}:{sorted unique engines}".

### Decisive source
```go
func ShouldBypassCacheForProxyMarket(q Query) bool {
	if q.ProxyURL == "" && q.ProxyOverride == "" { return false }   // direct ⇒ cacheable
	// proxied but NO market labels: same key could be different geo results:
	return q.ProxyCountry == "" && q.ProxyClass == "" && q.ProxyProvider == ""
}
// cacheEnvelopeIfEligible BYPASS cases:
if ShouldBypassCacheForProxyMarket(q) { RecordBypass(); return "BYPASS" }
if usedEngine != engineName { RecordBypass(); return "BYPASS" }   // don't cache fallback responses — primary must recover
switch v := payload.(type) { case *Envelope: if len(v.Results)==0 { BYPASS } }  // no empty-result poisoning
// HITs rewrite volatile meta only:
meta["request_id"]=...; meta["requested_at"]=...; delete(meta,"timestamp"); meta["took_ms"]=...
```

**Flow:** only JSON, non-extract, non-fast-mode responses are cached (extract content and format variants would bloat/pollute); X-Cache header ∈ {HIT, MISS, BYPASS}; stats expose hits/misses/bypasses/evictions; expired entries pruned on every Get/Set/Stats; oldest-created eviction at capacity; mega balanced mode additionally probes a partial-set key built from circuit-open-excluded engines.
**Invariant:** the country/class/provider triple is part of identity because "best" results differ per market even under one proxy URL; engine-order normalization keeps `engines=google,bing` and `bing,google` on one entry.
**Probe:** `go test ./core -run 'TestCache|TestDedicatedEndpointCaches|TestProxiedRequest'` (server_test.go pins both polarities of the market-bypass rule).
**Probe executed (real runner):** same command at pin = **2 top-level PASS** (proxied-with-market cached vs proxied-without-market bypassed), part of a fully green `go test ./core`.
**Python-equivalent probe (executed):**
```python
def bypass(proxy_url, override, pc, pcl, pp):
    if not proxy_url and not override: return False
    return not (pc or pcl or pp)
assert bypass("http://p","", "", "", "")==True    # unlabeled proxy → BYPASS
assert bypass("http://p","","DE","resi","bright")==False  # labeled → cacheable
assert bypass("",None,"","","")==False            # direct → cacheable
print("cache bypass matrix GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "BuildCacheKey ShouldBypassCacheForProxyMarket refreshCachedMeta buildMegaCacheKey", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt market-fields-in-key + the three BYPASS rules + meta-refresh-on-HIT; adapt TTL/size to your traffic; omit partial-set mega keys unless you run mixed-health engine sets.
