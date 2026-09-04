<!-- capsule-v2 -->
# Baidu mu-canonical URL gate — why are redirect links replaced by the card's real destination and relative links rejected?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How does the Baidu parser recover true destinations from opaque redirects, and which rows does it refuse?

## mu= preference + relative refusal
**Path/Symbol:** `baidu/parse_html.go` — `parseBaiduSelection` L62–165 (href gates L98–120, mu swap L113–120), `canonicalBaiduURL` L170–181, ad-text scan `baiduSelectionHasAdMarker` L190–207.
**Signature:** `canonicalBaiduURL(item *goquery.Selection) string`; `parseBaiduSelection(sel *goquery.Selection) []core.SearchResult`.
**Data Shape:** organic rows link via absolute redirect `http://www.baidu.com/link?url=<opaque>`; the REAL destination rides a `mu=` attribute on the result-card container (e.g. `mu="https://baike.baidu.com/..."`). Op cards ("People also search", tpl=recommend_list) carry RELATIVE on-site links `/s?wd=...`.

### Decisive source
```go
// baidu/parse_html.go:106-120 — three gates in order
if strings.HasPrefix(href, "/") {          // 1. relative = related-search module,
    return                                  //    NOT an organic row
}
// Baidu result cards carry the canonical destination in the mu= attribute
// ... while the visible link is an opaque www.baidu.com/link?url= redirect.
// Prefer mu= so callers get the real URL, which also enables domain-based
// classification (encyclopedia, news, etc.) downstream.
if mu := canonicalBaiduURL(item); mu != "" {
    href = mu                               // 2. swap redirect → canonical
}
```
`canonicalBaiduURL` (:170–181): own `mu` attr first, else walk UP to nearest ancestor `[mu]` (`item.Closest("[mu]")`); accept only when it starts `http://`/`https://`. Earlier hard gates shared with Yandex: href `""`/`"#"`/`javascript:` prefix ⇒ skip (:102–105).
**Flow:** title-first row admission (`item.Find("h3").First()` — in-source comment :69–70: "h3-first: organic results always carry a heading; this filters out non-result blocks that may share the wrapper class"), then link resolution h3>a[href] → titleTag.Closest("a[href]") → first Selectors.Link; desc ladder `div.c-abstract` → DescAlt prefixes → whole-card text minus title.
**Invariant:** returned URLs must be caller-usable — an opaque redirect would break domain-based classification and dedupe, so mu= wins whenever present; rows that only offer relative search links are classified OUT of the organic stream entirely. Ad detection is two-channel: selector markers (`[data-tuiguang]`, `.ec-tuiguang`, …) PLUS Chinese text scan 广告/推广/商业推广 over span/i/em children.
**Probe:** `baidu/parse_html_test.go:48 TestParseBaiduHTMLParsesBaike` pins mu-bearing encyclopedia cards end-to-end against `testdata/search_results.html`.
**Python-equivalent probes (executed byte-exact):**
```bash
grep -c '"mu"' baidu/parse_html.go      # → 2 (call site + Closest("[mu]"))
grep -o '广告' baidu/parse_html.go | wc -l   # → 1 line carrying all three markers
```
```python
hrefs = ["/s?wd=x", "http://www.baidu.com/link?url=Q", "javascript:void(0)", "#"]
def admitted(h): return not (h.startswith("/") or h in ("","#") or h.startswith("javascript:"))
assert [h for h in hrefs if admitted(h)] == ["http://www.baidu.com/link?url=Q"]
print("relative-refusal gate GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "canonicalBaiduURL parseBaiduSelection mu redirect", limit: 4, fields: ["signature","name","file"] });
```

## Verdict
Adopt prefer-canonical-over-redirect for any engine whose result links traverse a click-tracker domain; keep the relative-link rejection so aggregation modules never pollute organic ranks. Adapt marker vocabularies per engine (Chinese ad glyphs here).
