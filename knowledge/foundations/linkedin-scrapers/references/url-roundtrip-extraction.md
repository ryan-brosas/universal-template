<!-- capsule-v2 -->
# URL round-trip extraction — how do I pull clean canonical job URLs out of a DOM listing without a schema?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c` (≡ linkedin_scraper); Codebase Memory `joeyism-linkedin-scraper`. **Question:** what is the minimal correct contract for extracting deduplicated absolute URLs from link elements?

## The extractor
**Path/Symbol:** `linkedin_scraper/scrapers/job_search.py:JobSearchScraper.search/_build_search_url/_extract_job_urls` (:41–145); base helpers from `scrapers/base.py` (scraper-base-callbacks).
**Signature:** `async search(keywords=None, location=None, limit=25) -> List[str]`; `await page.wait_for_selector('a[href*="/jobs/view/"]', timeout=10000)` in try/except returning `[]` on timeout (no results ≠ error); `_extract_job_urls(limit)` walks `locator('a[href*="/jobs/view/"]').all()`.
**Data Shape:** output is a list of ABSOLUTE, query-stripped, deduped URL strings; input hrefs may be relative (`/jobs/view/...`) or carry tracking queries.

### Decisive source
```python
clean_url = href.split('?')[0] if '?' in href else href   # 1. strip tracking query
if not clean_url.startswith('http'):                      # 2. absolutize
    clean_url = f"https://www.linkedin.com{clean_url}"
if clean_url not in seen_urls:                            # 3. dedupe AFTER normalization
    job_urls.append(clean_url); seen_urls.add(clean_url)
```

**Flow:** build minimal search URL via urlencode({keywords, location}) → navigate → wait_for_selector as an EXISTENCE probe (timeout = honest empty result) → bounded scroll (`max_scrolls=3`) to trigger lazy cards → per-link try/except island: normalize → dedupe → stop at limit. Callback progress events fire at fixed milestones (20/50/90/100) around the phases.
**Invariant:** dedupe happens AFTER query-strip + absolutization, never on raw hrefs — the same job reached via two tracking URLs must collapse to one entry; the limit check runs BEFORE processing each link so over-collection stops early; individual link failures log-and-continue (per-item isolation), never abort the batch.
**Probe:** integration-gated behind live session fixtures (tests/test_job_scraper.py requires linkedin_session.json — coverage caveat: unit-run only with credentials). Deterministic probes: needle `seen_urls` + `split('?')[0]` at :135–141; graph probe resolves JobSearchScraper.search.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "JobSearchScraper _extract_job_urls", limit: 10 });
```

## Verdict
Adopt: selector-gated existence probe, normalize-then-dedupe ordering, pre-check limit break, per-link exception islands. Adapt the href substring and base origin per site. Omit the callback milestones if your host has its own progress channel. Pass-10 recorded this file as "pure composition" of existing capsules; promoted because the normalize-then-dedupe ORDERING is a distinct porting trap no earlier capsule pinned.
