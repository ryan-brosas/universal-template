<!-- capsule-v2 -->
# Yandex lr-not-rstr region policy — which URL parameters deliberately trade geo precision for fewer captchas?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** How is Yandex region targeting encoded, and what was deliberately dropped?

## The dropped param
**Path/Symbol:** `yandex/url.go` — `BuildURL` L15–54 (web), `BuildImageURL` L58–95 (images), `yandexLR` L97–99; base `https://www.yandex.com`, paths `/search/` and `/images/search/`.
**Signature:** `BuildURL(q core.Query, page int) (string, error)` — Yandex paginates via `p=<page>` (0-based), unlike Baidu's raw `pn=<offset>`.
**Data Shape:** text operators folded into `text=`: ` site:<site>`, ` mime:<filetype>`, ` date:<interval>`, ` lang:<language-subtag>`; region as separate `lr=` param resolved by `core.ResolveRegion(region).YandexLR`.

### Decisive source
```go
// yandex/url.go:45-50 — the anti-captcha ruling, verbatim
if lr := yandexLR(q.Region); lr != "" {
    params.Add("lr", lr)
    // rstr (strict region) dropped - it makes Yandex captcha far more
    // often. lr alone still ranks toward the region, just less precisely.
    // params.Add("rstr", "true")
}
```
The same block (with identical comment) appears in `BuildImageURL` :86–91. Locale guard :31–35: only when `ParseLocale(q.LangCode).Language != ""` does ` lang:` get appended — and per in-source comment the operator accepts the lowercase LANGUAGE subtag only; region modifiers must ride `lr=`.
**Flow:** empty effective text ⇒ error `"empty query built"` (checked AFTER operator folding, :41–43/:74–76); images take `site=` and `itype=` as REAL params (:78–84) instead of folded operators.
**Invariant:** never send `rstr=true` — strict-region mode measurably raises captcha frequency at Yandex's edge, and the loss of ranking precision is the accepted price. Numeric regions pass through verbatim as `lr` (region-uule capsule). This is a deliberate precision-for-stealth trade, documented IN SOURCE so porters don't "restore" the missing param.
**Probe:** `yandex/url_test.go:TestBuildURL*` fixture round-trips (101 lines); integration-gated live checks.
**Python-equivalent probe (executed byte-exact):**
```bash
grep -o 'rstr' yandex/url.go | wc -l   # → 4: TWO commented-out Add calls + TWO comment mentions, zero active uses
```
```python
# p-page pagination vs offset pagination
def yandex_pages(start, size=10): page, skip = divmod(start, size); return page, skip
assert yandex_pages(35) == (3, 5)   # BuildURL gets p=3; caller skips 5 organics on that page
print("yandex url dialect GREEN")
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "BuildURL BuildImageURL yandexLR ResolveRegion", limit: 4, fields: ["signature","name","file"] });
```

## Verdict
Adopt the document-the-dropped-param discipline: when a parameter hurts more than it helps, leave the commented-out corpse with a reason. Adapt the operator set (`lang:`/`mime:` are Yandex-specific search operators, not query params). Omit for engines without regional edge throttling.
