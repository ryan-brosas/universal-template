<!-- capsule-v2 -->
# llms.txt generator — sitemap to curated AI index with bomb limits and freshness ordering

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you turn an arbitrary XML sitemap into a safe, ordered llms.txt without sitemap-bomb DoS?

## Recursive fetch with shared budget + priority/changefreq sort + section assembly
**Path/Symbol:** `src/geo_optimizer/core/llms_generator.py:fetch_sitemap` (61–235), `generate_llms_txt` (352–487), `discover_sitemap` (495–594).
**Signature:** `fetch_sitemap(sitemap_url, on_status=None, _depth=0, _total_count=None, session=None) -> list[SitemapUrl]`; `generate_llms_txt(base_url, urls, site_name=None, description=None, fetch_titles=False, max_urls_per_section=20) -> str`.
**Data Shape:** `SitemapUrl(url, lastmod, priority, changefreq)`; limits from config: `_MAX_SITEMAP_DEPTH=3`, `MAX_SUB_SITEMAPS=10`, `MAX_TOTAL_URLS=10_000`, body cap 10 MB.

### Decisive source
```python
# fix #124: initialize shared counter across recursive calls (mutable-list trick)
if _total_count is None:
    _total_count = [0]
if _total_count[0] >= MAX_TOTAL_URLS:
    return urls                       # checked BEFORE fetch AND inside both loops
...
# freshness rank: lower value = fresher; priority DESC then changefreq ASC
_CHANGEFREQ_RANK = {"always": 0, "hourly": 1, "daily": 2, "weekly": 3,
                    "monthly": 4, "yearly": 5, "never": 6}
def _sort_key(u):
    return (-u.priority, _CHANGEFREQ_RANK.get(u.changefreq or "", 7))
```

**Flow:** discovery tries robots.txt `Sitemap:` lines first (#116, same-domain check + SSRF validation) then six common paths via HEAD with GET fallback on 405/exception → recursive index walk bounded by depth/sub-sitemaps/shared URL counter, session reused across hops (#122), streamed body capped mid-download → per-URL: normalize relative, `url_belongs_to_domain` (exact-or-subdomain, never substring), skip-pattern filter (`/wp-, /admin, .*.(xml|json|pdf)...` precompiled regexes #123), dedupe, categorize via pattern table → emit header `# name` + `> description`, homepage line, main sections in `SECTION_PRIORITY_ORDER` capped at 20 links each, then a single `## Optional` section (legal/contact/etc., ≤5 each) that short-context LLMs may skip.
**Invariant:** Every network hop re-validates SSRF and streams with size caps — recursion multiplies attack surface so the budget must be SHARED across the whole tree (a mutable one-element list), not per-call. Labels fall back title→fetched-page-title→slug-derived; numeric-only slugs escalate to two path segments.
**Probe:** `tests/test_cli.py::test_llms_with_sitemap_found` + `tests/test_v2_remaining_fixes.py` generator suites (+ `tests/test_batch_audit.py` reusing `fetch_sitemap`; `PYTHONPATH=src pytest tests/test_cli.py tests/test_batch_audit.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "generate_llms_txt changefreq sitemap", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt shared-budget recursion, sort key, and Optional-section semantics for any sitemap→index generator; adapt category patterns/skip lists per site; omit WordPress-specific paths if unneeded.
