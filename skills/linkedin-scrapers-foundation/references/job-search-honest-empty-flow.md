<!-- capsule-v2 -->
# Honest-empty search flow — what should a search scraper return when LinkedIn shows no results, and how little scrolling do search cards actually need?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85b…`; Codebase Memory `joeyism-linkedin-scraper`. **Question:** how do I structure search-results scraping so empty results are honest data, and pagination effort is budgeted per surface?

## Gate on first card, return [] loudly, micro-scroll, cap extraction
**Path/Symbol:** `linkedin_scraper/scrapers/job_search.py:JobSearchScraper.search` (:41–83), `_build_search_url` (:85–101), `_extract_job_urls` (:103–145).
**Signature:** `async def search(self, keywords: Optional[str] = None, location: Optional[str] = None, limit: int = 25) -> List[str]`.
**Data Shape:** input = optional keywords/location (urlencode'd), limit cap; intermediate = results page; output = deduplicated absolute "/jobs/view/" URLs, length ≤ limit; empty page ⇒ [].

### Decisive source
```python
try:
    await self.page.wait_for_selector('a[href*="/jobs/view/"]', timeout=10000)
except:
    logger.warning("No job listings found on page")
    return []                                  # empty is DATA, not an error

await self.wait_and_focus(1)
await self.scroll_page_to_bottom(pause_time=1, max_scrolls=3)   # micro-budget vs feeds' 10+
...
for link in job_links:
    if len(job_urls) >= limit: break           # cap BEFORE touching each link
    clean_url = href.split('?')[0] if '?' in href else href
    if not clean_url.startswith('http'):
        clean_url = f"https://www.linkedin.com{clean_url}"
    if clean_url not in seen_urls:
        job_urls.append(clean_url); seen_urls.add(clean_url)
```

**Flow:** _build_search_url (urlencode only provided params; bare path when none) → navigate_and_wait (rate-limit fused) → 10s wait for FIRST job-card anchor → absent ⇒ warning + [] → wait_and_focus nudge (sleep+bring_to_front) → bounded scroll (pause=1s × max_scrolls=3) → limit-capped, seen-set-deduped extraction (query-strip → absolutize).
**Invariant:** no-results returns an EMPTY LIST through the success path (caller logic branches on len, never on exceptions); scroll budget is sized to the surface (search cards ≈3 scrolls vs feed scrollers' 10) — over-scrolling wastes rate-limit headroom; the limit check runs INSIDE the loop so oversized result pages stop early.
**Probe (executed):** pure-function probe of the URL builder — `_build_search_url(None,'software engineer','San Francisco, CA')` → `'https://www.linkedin.com/jobs/search/?keywords=software+engineer&location=San+Francisco%2C+CA'`; both params None → bare `'https://www.linkedin.com/jobs/search/'`. Live-DOM path integration-gated upstream (@pytest.mark.skip, selector rot recorded). Extraction internals already pinned by url-roundtrip-extraction.
**Runner-up:** Auto_job_applier_linkedIn's search-url builder (search-url-builder capsule) encodes filters as richer query strings; joeyism shows the minimal urlencode-only-what-you-have variant.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "JobSearchScraper search", limit: 6 });
// → search :41–83, _build_search_url :85–101, _extract_job_urls :103–145, conftest.test_job_search_params
```

## Verdict
Adopt the honest-empty contract (missing results ⇒ logged []) and surface-sized scroll budgets. Adapt selector, param names, and budgets as LinkedIn rotates them. Omit the bring_to_front nudge in headless hosts where it is a no-op. Coverage caveat: flow verified from source at HEAD + URL-builder executed live; card-side behavior inherits the upstream skip.
