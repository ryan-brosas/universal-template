<!-- capsule-v2 -->
# Result normalization — how do messy engine URLs become stable IDs, domains, and cluster keys?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What canonicalization must run before ID hashing/clustering so the same target always collides?

## normalizeURL pipeline
**Path/Symbol:** `core/response_builder.go:normalizeURL` (L293–332), `unwrapBingURL` (L333–362), `EnrichResult` (L40–99), `buildResultID` (L259–271).
**Signature:** `normalizeURL(raw string) string`; `ResultID(engine, url) string`; `EnrichResult(SearchResult, EnrichContext) Result`.
**Data Shape:** lowercase scheme+host; delete utm_*, fbclid, gclid, msclkid, ref, _ga; strip trailing slash except root; Bing `/ck/a?...u=a1<urlsafe-b64-nopad>` unwrapped by padding to %4 and swapping -_ → +/ before std base64 decode.

### Decisive source
```go
u.Scheme = strings.ToLower(u.Scheme)
u.Host = strings.ToLower(u.Host)
q := u.Query()
for _, p := range []string{"utm_source","utm_medium","utm_campaign","utm_term",
    "utm_content","fbclid","gclid","msclkid","ref","_ga"} { q.Del(p) }
...
func buildResultID(engine, normalizedURL string) string {
	return "s_" + shortMD5(engine+"|"+normalizedURL)   // md5[:16 hex]
}
```

**Flow:** SearchResult → normalizeURL → extractDomain (host minus www.) → buildDisplayURL breadcrumb (`domain › path › parts`, truncated 60 chars with …) → favicon `https://<domain>/favicon.ico` → DomainInfo (publicsuffix TLD/SLD + gov/edu/mil/news/forum/marketplace/social category from embedded YAML, override file via OPENSERP_ENRICHMENT_DOMAINS_FILE) → Classification (path heuristics: /wiki/, .pdf, /watch?v=, /forum|thread|questions …). Negative legacy ranks: `rank<=0 && !Ad && Type==""` ⇒ typed AnswerBox.
**Invariant:** IDs and cluster grouping hash ONLY the normalized URL (+engine); skipping unwrapBingURL splits one target into two clusters; computeResultPosition prefers AbsoluteRank, else Start+rank.
**Probe:** `go test ./core -run TestValidateResultType`; bing fixture suites exercise unwrap through ParseHTML; image dims parsed back out of Description ("Height:h, Width:w, Source Page: url") by parseImageDescription regexes.
**Probe executed (real runner):** `-run TestValidateResultType` = 1 PASS at pin; the full taxonomy (full/ad/related/similar/answer-box) green inside the package runs; Bing mixed-ads absolute-order and title-fallback suites = 16/16 PASS in `go test ./bing -v`.
**Python-equivalent probe (executed):**
```python
import base64, urllib.parse as up
raw="https://www.bing.com/ck/a?!&&p=x&u=a1aHR0cHM6Ly9leGFtcGxlLmNvbS9wYWdl"
q=up.parse_qs(up.urlparse(raw).query)['u'][0]
enc=q[2:]
enc += '='*((4-len(enc)%4)%4)
dec=base64.b64decode(enc.replace('-','+').replace('_','/')).decode()
assert dec=="https://example.com/page", dec
print("bing unwrap GREEN:", dec)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aao-openserp".replace("aao","aeo"), query: "normalizeURL unwrapBingURL EnrichResult buildResultID NormalizeURLForClustering", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt canonicalization-before-hashing and the tracking-param list; adapt the param list to your advertisers; omit the Bing unwrap if you don't parse Bing (but then exclude bing from clustering sources).
