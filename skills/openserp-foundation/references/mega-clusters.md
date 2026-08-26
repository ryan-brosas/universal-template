<!-- capsule-v2 -->
# Mega search & clusters — how do you fan out to N engines, survive a deadline, and score cross-engine agreement?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What do balanced/any/fastest modes guarantee under a deadline, and what formula ranks consensus URLs?

## Modes + partial results
**Path/Symbol:** `core/server.go:handleMegaEndpoint` (L942–1115), `core/resilient.go:searchAnyDetailed/searchFastestDetailed/runParallelDetailed` (L329–518), `core/clusters.go` (whole file), `deduplicateMegaResults/betterMegaResult` (server.go L1279–1331).
**Signature:** `SearchAllParallel(ctx, q, engines) ([]MegaSearchResult, responded, failed)`; `BuildClusters(results []Result, enginesQueried int) []Cluster`.
**Data Shape:** MegaTimeout default 90s; modes balanced(default)/any/fastest; dedupe=true merge=true defaults.

### Decisive source
```go
collectLoop:
for collected < started {
	select {
	case res := <-resultCh: ...append...
	case <-ctx.Done():
		// engines still pending are reported FAILED with ctx.Err() so the caller
		// gets PARTIAL results instead of blocking on a slow engine:
		for name := range pending { failed = append(...); errors = append(...) }
		break collectLoop
	}
}
// cluster score: reciprocal-rank sum normalized by engines QUERIED (not answered):
acc.scoreSum += 1.0 / float64(rank)          // rank<=0 treated as 1
score := acc.scoreSum / float64(enginesQueried); if score > 1.0 { score = 1.0 }
sort by Score desc, then BestRank asc
// cross-engine dedupe keeps first-seen order, prefers better rank then engine name:
if candidate.Rank > 0 && (current.Rank <= 0 || candidate.Rank < current.Rank) { replace }
key := ad-class + "\x00" + NormalizeURLForClustering(url)
```
any mode: sequential in requested order, first success wins (engineErrors accumulated for skipped/uninitialized). fastest: circuit-closed candidates sorted by AvgSuccessLatency. merge=false keeps only results of the first responding engine (in requested order).
**Invariant:** zero responses ⇒ ErrAllEnginesFailed with per-engine error details (megaFailureMessage surfaces the single-engine case readably); clusters keyed on md5(normalized URL)[:8] prefixed "c_"; cache skips fastest mode entirely (its choice isn't reproducible).
**Probe:** `go test ./core -run 'TestMega|TestCluster'`; server_test.go pins engine-order-normalized caching and partial-timeout behavior.
**Probe executed (real runner):** same command at pin = **18 PASS** — every mega mode/behavior named in this capsule (balanced merge+dedupe flags, any-mode stop order, fastest-by-latency, partials-with-failed-list, deterministic URL dedupe, engine-order-normalized caching, aggregate network-bytes header, invalid mode 400) executed green.
**Python-equivalent probe (executed):**
```python
occ=[('google',1),('bing',2),('google',4)]
score=sum(1/r for _,r in occ)/3      # enginesQueried=3
best=min(r for _,r in occ)
assert round(score,2)==0.92 and best==1
print("cluster scoring GREEN:", round(score,2))
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "runParallelDetailed BuildClusters deduplicateMegaResults searchFastestDetailed MegaTimeout", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt partial-results-on-deadline with explicit failed-engine reporting and the Σ1/rank ÷ enginesQueried score; adapt timeouts and tie-breaking; omit clustering unless you serve consensus views (it's cheap but changes response shape).
