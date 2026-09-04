<!-- capsule-v2 -->
# Dual parser — how do the live-browser path and POST /parse stay in agreement when selectors drift?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** Where must selector and classification logic live so rod-based search and stateless HTML parsing can't diverge?

## One selector table + one classifier, three consumers
**Path/Symbol:** `google/selectors.go` (whole file — "single source of truth" comment), `google/search_raw.go:classifyGoogleDocument` (L126–137), `bing/search.go:checkCaptcha/checkNoResults` (L45–80) mirroring `bing/parse_html.go:classifyBingDocument`, `core/html_parser.go:HTMLParser` interface.
**Signature:** `HTMLParser interface { Name() string; ParseHTML(io.Reader) ([]SearchResult, error) }`; `classify*Document(doc *goquery.Document) error`.
**Data Shape:** Selectors struct groups captcha/captcha-markers/soft-block/no-results/result-stats/results/ad/link/title/desc ladders/image selectors per engine.

### Decisive source
```go
// google/search.go — the LIVE page is classified through the same goquery rules:
func (gogl *Google) classifyPage(page *rod.Page, queryProxyURL string) error {
	err := core.ClassifyFromPage(page, classifyGoogleDocument)  // renders page→doc
	if info, infoErr := page.Info(); infoErr == nil && isGoogleSorryURL(info.URL) {
		err = core.ErrCaptcha                                  // /sorry/ URL check needs the LIVE url
	}
	if errors.Is(err, core.ErrCaptcha) && gogl.solveCaptchaOnPage(page, queryProxyURL) { return nil }
	return err
}
// shared primitive (page_helpers.go):
func ClassifyChallengeDocument(doc, s DocSignals) error   // selectors first (cheap), then lowercased text markers
```

**Flow:** raw Search: fetch → `classifyGoogleRawHTML(body)` → ParseHTML(bytes) → empty+ErrEmptyResult ⇒ `[]SearchResult{}, nil`; zero parseable rows without that signal ⇒ ErrParser. Browser Search: Navigate → classifyPage → WaitForElements → parse → re-classify if zero deduped rows. Server registers POST /{engine}/parse for every engine implementing HTMLParser.
**Invariant:** /bing/search and /bing/parse MUST agree — bing's live checks reuse the same marker lists (`pageTextContainsAny(page, Selectors.CaptchaMarkers)`); Google's sorry-URL check supplements (not replaces) the document classification because it requires response-URL state goquery can't see.
**Probe:** `go test ./google -run TestGoogleParseHTMLFixtures` (search_results/no_results/captcha/captcha_new/soft_block fixtures assert exact sentinel errors); sibling captcha_selector_test.go files pin each CaptchaPage selector matches its fixture.
**Probe executed (real runner):** same command at pin = **1 top-level PASS** covering all five fixtures as subtests; the shared-classifier claim holds across engines — Classify* suites (Google/Baidu/Yandex/Ecosia/DDG) all green inside their packages' whole-package runs (baidu 14, yandex 14, ecosia 17, duckduckgo 12 tests passed).
**Python-equivalent probe (executed):**
```bash
grep -n 'classifyGoogleDocument\|ClassifyChallengeDocument' google/*.go core/page_helpers.go | wc -l   # → 9 wiring points
grep -rn 'same way\|mirroring\|Mirrors' bing/search.go google/search.go | head -3
# → "classifies the live page the same way classifyBingDocument" / "runs the same captcha/soft-block/no-results rules the raw HTML path uses"
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "ParseHTML ClassifyChallengeDocument DocSignals classifyBingDocument HTMLParser", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the single-selector-table + shared-classifier architecture and the Has-before-Search probe pattern (banner-less pages must not eat the full timeout); adapt selectors per engine version; omit the solver hook if you have no captcha budget.
