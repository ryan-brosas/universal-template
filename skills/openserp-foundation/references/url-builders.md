<!-- capsule-v2 -->
# URL builders — how does one Query struct map onto six engines' incompatible parameter dialects?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** Where do site/filetype/date/locale filters get folded per engine, and which params are deliberately omitted?

## Per-engine dialects
**Path/Symbol:** `google/url.go:BuildURL` (L229–307), `duckduckgo/url.go:buildParams/BuildURL` (L82–180), `yandex/url.go:BuildURL` (L15–50), `ecosia/url.go:ecosiaFreshness/BuildURL` (L22–90), `bing/url.go:BuildURL`, `baidu/url.go`.
**Signature:** `BuildURL(q core.Query) (string, error)` or `BuildURL(q, page int)` — engines paginate differently.
**Data Shape:** shared inputs Text/LangCode/Region/DateInterval(YYYYMMDD..YYYYMMDD)/Filetype/Site/Limit/Start/Filter.

### Decisive source
```go
// google — operators folded into q; anti-personalization defaults:
text += " site:" + q.Site;  text += " filetype:" + q.Filetype
if q.Limit > 10 { params.Add("num", strconv.Itoa(q.Limit)) }
params.Add("tbs", fmt.Sprintf("cdr:1,cd_min:%s,cd_max:%s", ...))
params.Add("pws", "0"); params.Add("sourceid", "chrome")
if !q.Filter { params.Add("filter", "0") }   // google default is filter=1
// duckduckgo — kl uses INVERTED region-language ("uk-en" for en-GB):
"en-gb": "uk-en", "zh-tw": "tw-zh", "el": "gr-el"
df = start.Format("2006-01-02")+".."+end.Format("2006-01-02"); t=h; ia=web; s=page*25
// yandex — filetype/lang as SEARCH OPERATORS, region via lr only:
text += " mime:" + q.Filetype; text += " lang:" + locale.Language
// lr alone; rstr dropped — it makes Yandex captcha far more often
// ecosia — freshness bucketed, malformed input REJECTED not silently dropped:
span <=24h→"day"; <=7d→"week"; <=31d→"month"; else "" (no finer control)
```

**Flow:** every builder errors on empty effective query (`empty query built`); Google image adds tbm=isch; DDG images add iax/ia=images; Ecosia images live on /images with imageType ∈ {clipart,photo,line,animatedgif,transparent} validated against a set (error on unsupported).
**Invariant:** never send an unrecognized locale param (DDG returns "" → param omitted); date-interval format errors are hard errors so filters never silently vanish; Yandex numeric region passes through verbatim as lr.
**Probe:** `yandex/url_test.go`, `google/search_raw_test.go` fixture round-trips, per-engine integration tests (tag-gated).
**Probe executed (real runner):** repaired to real symbols: `go test ./yandex ./google -run 'TestBuildURL|TestYandexLR|TestBuildImageURL'` = **3 PASS** at pin; per-engine URL/page-type suites all green in whole-package runs (`./google` 20 page-type subtests, `TestBuildSearchURL/TestBuildURL/TestBuildImageURL` ×32+15+12 cases).
**Python-equivalent probe (executed):**
```python
from datetime import datetime, timedelta
s=datetime(2026,8,1); e=datetime(2026,8,20); span=e-s
bucket = "day" if span<=timedelta(days=1) else "week" if span<=timedelta(days=7) else "month" if span<=timedelta(days=31) else ""
assert bucket=="month"
print("ecosia freshness bucket GREEN:", bucket)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "BuildURL BuildImageURL duckDuckGoKL ecosiaFreshness yandexLR", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the fold-filters-into-q pattern and the reject-malformed-dates rule; adapt the exact param names when engines change their contracts; omit engines you don't serve.
