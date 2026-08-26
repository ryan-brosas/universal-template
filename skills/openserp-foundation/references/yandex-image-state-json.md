<!-- capsule-v2 -->
# Yandex data-state image JSON — how are image results harvested from embedded state blobs instead of DOM scraping?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How does the Yandex IMAGE search extract results, and what is its selector-fallback order?

## State-blob harvest
**Path/Symbol:** `yandex/search.go` — `SearchImage` L288–380, `parseImageEntities` L171–189; structs L16–37 (`ImageEntity`, `ImageData`); selectors in `yandex/selectors.go:37–39`.
**Signature:** `SearchImage(ctx, query) ([]core.SearchResult, error)`; `parseImageEntities(items rod.Elements) map[string]ImageEntity`.
**Data Shape:** each candidate node carries a `data-state` attribute holding JSON: `{initialState:{serpList:{items:{entities:{<id>:ImageEntity}}}}}` (note the source's own misspelling `InitalState` — the Go struct field is `InitalState` with json tag `"initialState"`, so it decodes regardless). Entity fields: `id`, `pos`(→Rank), `origWidth/origHeight`, `alt`(→Title), `origUrl`, `image`(thumb), `freshnessCounter`, `gifLabel`.

### Decisive source
```go
// yandex/search.go:314-325 — THREE-TIER selector fallback before classifying
results, _, err := core.WaitForElements(ctx, page,
    append([]string{Selectors.ImageItems}, Selectors.ImageItemsAlt...), // "div[role='main'] div[data-state]", "div[data-state*='serpList']"
    yand.GetSelectorTimeout())
if err != nil {
    if allStateNodes, allErr := page.Elements(Selectors.ImageStateAll); allErr == nil && len(allStateNodes) > 0 {
        results = allStateNodes   // tier 3: ANY div[data-state] on the page
        err = nil
    }
}
// :337-346 — and if parsing THOSE yields zero entities, re-parse ImageStateAll once more
```
Row assembly (:348–361): `Rank: img.Rank + 1`; `Description: fmt.Sprintf("%dx%d, freshness:%s, thumb_url:%s", W, H, Freshness, ThumbURL)`; early-exit `done=true` when `len(searchResults) >= query.Limit`. Tail: sort by Rank ascending then `DeduplicateResults`. Error path differs from web search: after classify, BOTH captcha and empty cases fall through to `return false, core.ErrSearchTimeout` (:326–335) — image search has NO partial-success funnel.
**Flow:** per-page loop keyed on `core.ShouldFetchResultPage(len(searchResults), query.Limit, searchPage)` with `BuildImageURL(query, searchPage)` (`p=<page>` param, `site=` / `itype=` params rather than text operators).
**Invariant:** entities merge into one map ACROSS nodes (`for id := range ... entities[id] = entity`) so duplicate ids dedupe silently; zero entities ⇒ `done=true` terminates cleanly (empty success). The fallback ladder is load-bearing because Yandex rotates which container carries state blobs.
**Probe:** fixture-level direct tests live at the parse layer; selector truth pinned by `yandex/captcha_selector_test.go:12 TestYandexPageTypeSelectors` pattern. Deterministic probes below carry gate 5.
**Python-equivalent probes (executed byte-exact):**
```bash
grep -c 'ImageStateAll' yandex/selectors.go yandex/search.go   # → 2 + 2
grep -n '"mu"\|InitalState' yandex/search.go | head -2         # → InitalState struct field
```
```python
import json
state = '{"initialState":{"serpList":{"items":{"entities":{"e1":{"id":"e1","pos":0,"origUrl":"https://x/a.jpg","alt":"A","origWidth":800,"origHeight":600,"image":"t.jpg","freshnessCounter":"7","gifLabel":false}}}}}}'
ent = json.loads(state)["initialState"]["serpList"]["items"]["entities"]["e1"]
assert ent["pos"] + 1 == 1   # Rank: img.Rank + 1 contract
print("image state-blob decode GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "parseImageEntities SearchImage data-state serpList", limit: 4, fields: ["signature","name","file"] });
```

## Verdict
Adopt state-blob-over-DOM harvesting whenever a SERP embeds its result payload as JSON attributes — it survives CSS churn far better than selector trees. Adapt the three-tier selector ladder to the target site's actual containers; keep the map-keyed id dedupe.
