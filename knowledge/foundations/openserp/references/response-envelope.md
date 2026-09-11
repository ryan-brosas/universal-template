<!-- capsule-v2 -->
# Response envelope — what does a client loop need for pagination, and which formats get cached?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How are has_more/next_start computed, and why are markdown/text/ndjson renderings never cached?

## Envelope v2.1
**Path/Symbol:** `core/response.go` (whole file), `core/server.go:resolveFormat/sendEnvelope` (L1590–1632).
**Signature:** `NewEnvelope(q, requestID, startedAt, engines) *Envelope`; `(e) Finalize(startedAt, q)`; `sendEnvelope(c, format, env) error`.
**Data Shape:** Envelope{query echo (text/lang/region/engines_requested), meta{request_id, requested_at, took_ms, engines_responded, engines_failed, engine_errors[], version:"2.1"}, results[]Result, serp_features[], pagination{page,has_more,next_start}, clusters?}.

### Decisive source
```go
func (e *Envelope) Finalize(startedAt time.Time, q Query) {
	e.Meta.TookMs = time.Since(startedAt).Milliseconds()
	limit := q.Limit
	if limit <= 0 { limit = defaultQueryLimit }        // 10
	page := q.Start/limit + 1
	e.Pagination = Pagination{
		Page:      page,
		HasMore:   countNonAdResults(e.Results) >= limit, // ads don't count!
		NextStart: q.Start + limit,
	}
}
// server.go — non-JSON formats bypass the cache entirely:
case "markdown": return c.Send(RenderMarkdown(env))
```

**Flow:** handler builds envelope → enriches results → Finalize stamps took_ms + pagination → format switch (json default; markdown/text/ndjson via Accept header fallback). Markdown renderer orders feature sections AI-summary→…before results, related-searches etc after; unknown new feature types are APPENDED by featureRenderOrderAfterResults so they're never dropped; extracted content is re-leveled with shiftMarkdownHeadings(+4, capped at h6).
**Invariant:** has_more counts only non-ad results (client loops otherwise stop early on ad-heavy pages); NextStart advances by limit even when fewer rows returned; cache stores JSON only — format variants would pollute the JSON cache; cached HITs refresh meta.request_id/requested_at/took_ms but keep results.
**Probe:** `go test ./core -run TestEnvelopePaginationCountsOrganicResults` (2 ads + 1 organic @limit=2 ⇒ has_more=false).
**Probe executed (real runner):** same command at pin = **1 PASS** (ads excluded from the limit count; NextStart arithmetic pinned by siblings TestPaginatedPositionUsesAbsoluteRank/TestLimitOrganicResultsDoesNotCountAds in the green ./core run).
**Python-equivalent probe (executed):**
```python
results=[{'Type':'ad'},{'Type':'ad'},{'Type':'organic'}]; limit=2
non_ad=sum(1 for r in results if r['Type']!='ad')
assert (non_ad>=limit)==False
print("pagination GREEN: has_more=False with", non_ad,"organic < limit", limit)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "Envelope Finalize Pagination RenderMarkdown resolveFormat refreshCachedMeta", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the organic-only has_more rule and meta-refresh-on-HIT; adapt field names to your API surface; omit ndjson/markdown renderers if you serve machines only.
