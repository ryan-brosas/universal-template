<!-- capsule-v2 -->
# Yandex browser-path partial-success captcha funnel — how does pagination survive a mid-run captcha without discarding collected pages?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** When Yandex challenges page 3 of a paginated search, what does the caller get back?

## The funnel
**Path/Symbol:** `yandex/search.go` — `Yandex.Search` L193–284, inner closure `fetchPage` L215–257, error-adjudication loop L259–279; classification via `classifyPage` L66–68 → `core.ClassifyFromPage(page, classifyYandexDocument)`.
**Signature:** `Search(ctx context.Context, query core.Query) ([]core.SearchResult, error)`; `fetchPage() (done bool, err error)` — `done=true` ends the outer loop WITHOUT error.
**Data Shape:** per page: `BuildURL(query, searchPage)` → `Navigate` → `waitForParsedResults(ctx, page, pageNum, wantOrganic)` → on wait-error a switch over `classifyPage`: `ErrCaptcha` → return `(false, core.ErrCaptcha)`; `ErrEmptyResult` → return `(true, nil)` (empty is SUCCESS-terminated, not an error); anything else → `(false, core.ErrSearchTimeout)`.

### Decisive source
```go
// yandex/search.go:261-271 — THE invariant
done, err := fetchPage()
if err != nil {
    // Yandex commonly challenges rapid pagination, so a later page can
    // be blocked after earlier pages already succeeded. Don't discard
    // what we have: return the collected results and only surface the
    // error when the first page itself yielded nothing.
    if core.CountOrganicResults(allResults) == 0 {
        return nil, err          // first-page failure = real failure
    }
    yand.logger.Warn("Pagination stopped after page %d (%s); returning %d collected results", ...)
    break                        // later-page failure = partial success (nil error)
}
```
Success tail: `limited := core.LimitOrganicResults(core.DeduplicateResults(allResults), query.Limit)` then `AttachFeaturesToFirstResult(limited, pageFeatures)` — features extracted ONLY on `searchPage == startPage`.

**Flow:** `PrepareEngineContext` + receiver-scope copy (`scoped := *yand` so per-request logger never races) → `ComputePagination(query.Start, 10)` gives `(startPage, skipOnFirstPage)` → loop guard `core.ShouldFetchResultPage(CountOrganicResults(allResults), query.Limit, searchPage-startPage)` → between pages `SleepContext(ctx, pageSleep=1s)`.
**Invariant:** captcha on page N>1 degrades to "return what you have" (error swallowed, logged as Warn); captcha/timeout on page 1 (zero organic collected) propagates. Empty-result is `done=true`, never an error. `wantOrganic` clamps to pageSize=10 and adds `skipOnFirstPage` when resuming mid-page.
**Probe:** `yandex/parse_html_test.go:88 TestParseYandexHTMLAdsDoNotConsumeOrganicRank` (rank math feeding CountOrganicResults); direct test for the funnel itself is integration-gated (`search_integration_test.go`).
**Python-equivalent probe (executed):**
```python
def should_return_error(err, organic_collected): return organic_collected == 0 and err is not None
assert should_return_error("captcha", 0) is True      # page-1 block = propagate
assert should_return_error("captcha", 20) is False    # mid-run block = partial success
print("partial-success funnel GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "classifyYandexDocument captcha classifyPage", limit: 4, fields: ["signature","name","file"] });
```
Live at pin: rank-1 `yandex.classifyYandexDocument` parse_html.go:30–35, rank-3 `yandex.classifyPage` search.go:66–68 (total:49).

## Verdict
Adopt the count-guarded partial-return ladder verbatim — it converts captchas from hard failures into degraded successes, which is the correct contract for any paginated scraper behind an adversarial edge. Adapt the 10-row page size and 1s inter-page sleep to the engine you port.
