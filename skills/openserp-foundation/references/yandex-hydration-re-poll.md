<!-- capsule-v2 -->
# Yandex hydration re-poll — how does the browser path wait for a progressively-rendered result list without reloading?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How do you parse a SERP whose rows stream in AFTER the results selector first appears?

## Grace-window re-poll
**Path/Symbol:** `yandex/search.go` L136–169 — consts `resultHydrationGrace = 2 * time.Second`, `resultPollInterval = 120 * time.Millisecond` (L139–142); `waitForParsedResults(ctx, page, pageNum, wantOrganic)`; shared selector-wait primitive `core.WaitForElements` (`core/page_helpers.go:28–65`).
**Signature:** `waitForParsedResults(ctx, page, pageNum, wantOrganic int) ([]core.SearchResult, error)`; `core.WaitForElements(ctx, page, selectors []string, timeout time.Duration) (rod.Elements, string, error)`.
**Data Shape:** phase 1 waits for ANY of `Selectors.Results` (`li[data-fast], li.serp-item`) up to engine `GetSelectorTimeout()`; phase 2 re-polls while `CountOrganicResults(results) < wantOrganic` AND `now < deadline(2s)`; each tick sleeps 120ms and re-reads `page.Elements(Selectors.Results)`.

### Decisive source
```go
// yandex/search.go:156-166
for core.CountOrganicResults(results) < wantOrganic && time.Now().Before(deadline) {
    if err := core.SleepContext(ctx, resultPollInterval); err != nil {
        return results, err            // ctx cancel returns PARTIAL results + err
    }
    nextElements, eerr := page.Elements(Selectors.Results)
    if eerr != nil || len(nextElements) <= len(elements) {
        continue                       // no GROWTH = skip reparse entirely
    }
    elements = nextElements
    results = yand.parseResults(nextElements, pageNum)
}
return results, nil                   // grace expiry is NOT an error: short page wins
```
Why it exists (in-source comment :136–138): "Yandex hydrates the results list progressively, so the first parse can be short." `WaitForElements` alone can't solve this — its probe fires on FIRST match of any selector, which happens before all rows render.

**Flow:** caller computes `wantOrganic = min(max(query.Limit,?),10)` (+skipOnFirstPage on resume pages); timeout of phase 1 is NOT swallowed here — it propagates so the caller's captcha/empty classifier can inspect the page.
**Invariant:** growth-gated (`len(nextElements) <= len(elements)` ⇒ continue) so unchanged DOMs are never reparsed; grace expiry returns the SHORT page as success; context cancellation mid-grace returns partials WITH error. The same 120ms cadence is `pollInterval` inside core WaitForElements — one rhythm for both phases.
**Probe:** direct tests are fixture-level (`yandex/parse_html_test.go:59 TestParseYandexHTMLFallbackSelectors` pins the selectors this loop polls); timing loop itself is integration-gated — deterministic probes below carry gate 5.
**Python-equivalent probes (executed byte-exact):**
```bash
grep -n 'resultHydrationGrace\|resultPollInterval' yandex/search.go   # → :140/:141 consts + :155/:157 uses
```
```python
# growth-gate semantics re-derived live from source
def keep_polling(got_organic, want, now, deadline, next_len, cur_len):
    return got_organic < want and now < deadline and not (next_len <= cur_len)
assert keep_polling(5, 10, 100, 102, 12, 8) is True
assert keep_polling(5, 10, 100, 102, 8, 8) is False   # no growth → continue (no reparse)
assert keep_polling(10, 10, 100, 102, 20, 18) is False # satisfied → stop
print("hydration re-poll GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "WaitForElements pollInterval hydration SleepContext", limit: 4, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-phase wait (selector-appear then count-to-target grace window) for any SPA that streams rows; adapt the 2s/120ms constants per engine's observed render latency. Omit for static HTML engines (Baidu raw path needs none).
