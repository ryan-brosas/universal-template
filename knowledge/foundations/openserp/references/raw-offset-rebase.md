<!-- capsule-v2 -->
# Raw offset-rank rebasing — how does a single-page raw fetch pretend it started at result #35?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How do Start-offset results get correct Rank and AbsoluteRank when the raw path fetches exactly ONE page?

## The rebase trio
**Path/Symbol:** `yandex/parse_html.go` — `skipOrganicResults` L150–163, `rebaseOrganicRanks` L165–177, `offsetAbsoluteRanks` L179–188; applied in `yandex/search_raw.go:64–68`; baidu twin inline at `baidu/search_raw.go:58–68`.
**Signature:** `rebaseOrganicRanks(results []core.SearchResult, start int)`; `offsetAbsoluteRanks(results, start int)`; `skipOrganicResults(results []core.SearchResult, skip int) []core.SearchResult`.
**Data Shape:** raw engines fetch page `start/10` once; the parse assigns LOCAL ranks 1..N; three post-passes convert local → global: skip `start%10` organic rows (ads preserved), then organic Rank += query.Start, then AbsoluteRank += startPage*10.

### Decisive source
```go
// yandex/search_raw.go:64-68 — order matters
if skipOnFirstPage > 0 {
    parsedResults = skipOrganicResults(parsedResults, skipOnFirstPage)
}
rebaseOrganicRanks(parsedResults, query.Start)      // organic Rank = start + local
offsetAbsoluteRanks(parsedResults, startPage*10)    // absolute += page*pageSize

// yandex/parse_html.go:150-162 — ads are NEVER skipped
func skipOrganicResults(results []core.SearchResult, skip int) []core.SearchResult {
    out := results[:0]
    for _, result := range results {
        if !result.Ad && skip > 0 { skip--; continue }   // only organics burn skip budget
        out = append(out, result)
    }
    return out
}
```
Baidu twin (:58–68) inlines both bumps per row (`AbsoluteRank > 0` guard, `Ad ⇒ continue` before Rank bump) — same contract, no helpers.
**Flow:** `ComputePagination(query.Start, 10)` yields `(page, skip)`; BuildURL paginates by that page; classification gates run BEFORE parsing so captcha pages never reach the rebase.
**Invariant:** rank math must stay consistent with browser-path pagination — after dedupe+limit, `results[i].Rank == query.Start + localIndex` for organics regardless of transport. Ads keep their own negative-ish stream untouched (rank-state capsule); zero-value AbsoluteRank (>0 guard) is left alone rather than shifted.
**Probe:** fixture round-trips `yandex/search_raw_test.go:16 TestYandexParseHTMLFixtures`; arithmetic carried by deterministic probes below.
**Python-equivalent probe (executed):**
```python
def compute_pagination(start, size=10): return start // size, start % size
rows = [("ad", True)] + [("o%d" % i, False) for i in range(1, 8)]
def skip_organic(rows, skip):
    out = []
    for name, ad in rows:
        if not ad and skip > 0: skip -= 1; continue
        out.append((name, ad))
    return out
page, sk = compute_pagination(35)
kept = skip_organic(rows, sk)                       # 5 organic rows burned, ad kept
ranks = [n for n, ad in kept if not ad]
assert ranks == ["o6", "o7"]                        # locals 6..7 survive skip of 5
assert [35 + 1, 35 + 2] == [36, 37]                 # rebased = start + local index
print("offset rebase GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "rebaseOrganicRanks offsetAbsoluteRanks ComputePagination", limit: 4, fields: ["signature","name","file"] });
```

## Verdict
Adopt the skip→rebase→offset ORDER (skipping after rebasing would shift the wrong rows) and the ad-immunity rule. Adapt only the page-size constant per engine.
