<!-- capsule-v2 -->
# llms.txt short-circuit — when can an extractor skip HTML scraping entirely?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** Under which conditions is /llms-full.txt or /llms.txt trusted as the extraction result, and how are SPA shells rejected?

## tryLLMSTxt
**Path/Symbol:** `extract/llmstxt.go` (whole file), gated from `extract/extractor.go:Extract` (L42–46).
**Signature:** `(e *Extractor) tryLLMSTxt(ctx, req, startedAt) (*ExtractResult, bool)`; `isSiteRoot(rawURL) bool`; `looksLikeHTML(text) bool`.
**Data Shape:** candidates ["/llms-full.txt", "/llms.txt"] (full corpus first, curated index second); minLLMSTxtRunes 200; per-candidate fetch timeout = req.Timeout.

### Decisive source
```go
if e.RawFetch == nil || !isSiteRoot(req.URL) { return nil, false }
// only roots: /llms.txt describes the WHOLE site — a deep page would get the
// site index and MISS the content the caller asked for.
path := strings.Trim(parsed.Path, "/"); return path == ""
...
body := resp.Body[:min(len,MaxBytes)]
text := strings.TrimSpace(string(body))
if len([]rune(text)) < minLLMSTxtRunes || looksLikeHTML(text) { continue }  // SPA shell: HTTP 200 but HTML
return &ExtractResult{ ..., ModeUsed: "llms_txt" }, true
// errors swallowed deliberately — missing llms.txt is the COMMON case:
if ferr != nil || resp.StatusCode != 200 { continue }
func looksLikeHTML(text string) bool {
	head := strings.ToLower(strings.TrimSpace(text)); if len(head)>256 { head=head[:256] }
	return HasPrefix("<!doctype html")||HasPrefix("<html")||Contains("<head>")||Contains("<body")
}
```
Title from the first markdown H1 (`# Title`) if the first non-blank line is one.
**Flow:** Extract checks UseLLMSTxt BEFORE any raw/rendered work; miss ⇒ silent fallthrough to normal extraction; hit returns immediately with meta.mode_used="llms_txt" so clients can see the provenance.
**Invariant:** never fail the extract because llms.txt probing failed; never accept an HTML body no matter how long; deep URLs never probe.
**Probe:** `go test ./extract -run TestExtractLLMSTxt` — TestExtractLLMSTxtRootHit / SkippedForDeepURL / RejectsHTMLShell pin all three rules.
**Probe executed (real runner):** same command at pin = **3 PASS** (all three rules executed green inside the 17-test ./extract package run).
**Python-equivalent probe (executed):**
```python
def looks_like_html(t):
    head=t.strip().lower()[:256]
    return head.startswith('<!doctype html') or head.startswith('<html') or '<head>' in head or '<body' in head
assert looks_like_html("<!DOCTYPE html><html><body>app</body></html>")
assert not looks_like_html("# Docs\n\n- [Guide](/guide): everything about the product. "+ "x"*200)
print("llms.txt HTML-sniff GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "tryLLMSTxt isSiteRoot looksLikeHTML llmsTxtCandidates minLLMSTxtRunes", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three gates (root-only, ≥200 non-HTML runes, candidate order); extend candidates if llmstxt.org grows conventions; omit if your targets don't publish llms.txt.
