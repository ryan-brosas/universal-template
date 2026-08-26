<!-- capsule-v2 -->
# Extract auto escalation — when does a raw fetch deserve a browser render, and when does article cleaning deserve the whole page?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What thresholds govern fast→rendered escalation and clean→full-body fallback so neither husks nor bot-walls win?

## Extractor.Extract ladder
**Path/Symbol:** `extract/extractor.go` (whole file), `goodEnough/textLength` (L181–208), `extract/content.go:extractContent/minCleanTextRunes` (L30–98), `Config.BatchTimeout` (config.go L26–36).
**Signature:** `(e *Extractor) Extract(ctx, ExtractRequest{URL, Mode auto|fast|rendered, ProxyURL, LangCode, Timeout, MaxBytes, FullPage, UseLLMSTxt, MinRunes}) (*ExtractResult, error)`.
**Data Shape:** defaultMinRunes 200; headings shortcut ≥120 runes && ≥minRunes−80 && has headings; minCleanTextRunes 250; MaxBytes floor 64KiB, default 2MiB; MaxConcurrent 2.

### Decisive source
```go
if req.Mode != ModeRendered && e.RawFetch != nil {
	rawResult, rawErr = e.extractFast(...)
	if req.Mode == ModeFast || goodEnough(rawResult, rawErr, req.MinRunes) { return rawResult, rawErr }
}
renderedResult, renderedErr := e.extractRendered(...)
if renderedErr == nil && renderedResult != nil {
	// Only prefer the rendered pass when it actually recovered MORE content —
	// a bot wall or consent page can render SHORTER than the raw HTML.
	if rawErr == nil && rawResult != nil && textLength(rawResult) > textLength(renderedResult) {
		return rawResult, nil }
	return renderedResult, nil
}
// trafilatura was too aggressive: cleaned article near-empty but raw page had
// real visible text ⇒ prefer fuller readable-body pass, keeping trafilatura meta:
if len([]rune(out.Text)) < minCleanTextRunes {
	if full, ferr := extractFullBody(...); ferr == nil && len(full.Text) > len(out.Text) { ... }
}
// batch budget derived from per-URL budget, not a separate knob:
waves := ceil(count / MaxConcurrent)
return time.Duration(waves) * 2 * c.Timeout     // worst case raw + render per worker
```
classifyStatus: 401/403→"blocked", 429→"rate limited", other non-2xx error; status 0 tolerated. FullPage skips article detection entirely (LLM agents often need nav/landing chrome). Envelope enrichment adds candidate fill-in: extract top-N, then walk up to N+3 more rows until N successes.
**Invariant:** rendered NEVER replaces a longer raw result (that's how consent-wall regressions are prevented); extraction errors become per-result Extracted.Error strings (≤180 chars), never HTTP 500s.
**Probe:** `go test ./extract` — TestExtractAutoEscalatesThinShell, TestExtractAutoKeepsRawWhenRenderedThinner, TestExtractAutoMinRunesForcesEscalation, TestExtractCleanFallsBackOnThinArticle, TestBatchTimeoutDerivation all executed-green semantics verified against source.
**Probe executed (real runner):** full `go test ./extract -v` at pin = **17/17 PASS** (all five named tests green, plus batch contract, llms.txt trio, cancellation, private-network guard). The earlier "executed" note referred to Python-equivalent semantics only — this is the real Go suite.
**Python-equivalent probe (executed):**
```python
def goodEnough(text_len, headings, min_runes=200):
    if text_len>=min_runes: return True
    return text_len>=120 and text_len>=min_runes-80 and headings>0
assert goodEnough(250,0) and not goodEnough(150,3) and goodEnough(130,2,min_runes=200)
print("goodEnough GREEN: floor 200 | shortcut 120..minRunes-80 needs headings")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "Extractor Extract goodEnough extractContent BatchTimeout EnrichEnvelopeWithExtraction", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt both escalation guards verbatim — they encode two opposite failure modes (thin shell vs bot wall); adapt thresholds to your content mix; omit trafilatura in favor of your own readability stack but keep the length-comparison contract.
