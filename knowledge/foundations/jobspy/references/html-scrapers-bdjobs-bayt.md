<!-- capsule-v2 -->
# BDJobs & Bayt — HTML card scraping with selector fallback ladders and responsibilities-section extraction

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How do the two HTML-scraping adapters (BDJobs, Bayt) find job cards with fallback selector ladders and extract structured fields from messy markup?

## BDJobs adapter
**Path/Symbol:** `jobspy/bdjobs/__init__.py:BDJobs` (42–353) — `scrape` (67–134), `_process_job` (136–249), `_get_job_details` (251–353); `jobspy/bdjobs/util.py` — `find_job_listings` (57–79), `parse_location` (9–29), `parse_date` (32–54), `is_job_remote` (82–99); `jobspy/bdjobs/constant.py` (`headers`, `search_params`, `job_selectors`, `date_formats`).
**Signature:** `BDJobs.scrape(scraper_input) -> JobResponse`; `_process_job(job_card: Tag) -> JobPost | None`; `_get_job_details(job_url) -> dict`.
**Data Shape:** `base_url="https://jobs.bdjobs.com"`, `search_url="https://jobs.bdjobs.com/jobsearch.asp"`; `delay=2`, `band_delay=3`; `seen_ids: set`; session `create_session(is_tls=False, has_retry=True, delay=5, clear_cookies=True)`.

### Decisive source
```python
# find_job_listings: try each selector in job_selectors (div.job-item, div.sout-jobs-wrapper, ...)
for selector in job_selectors:
    if "." in selector:
        tag_name, class_name = selector.split(".", 1)
        elements = soup.find_all(tag_name, class_=class_name)
        if elements and len(elements) > 0: return elements
# fallback: any <a href containing "jobdetail"> -> return link.parent elements
job_links = soup.find_all("a", href=lambda h: h and "jobdetail" in h.lower())
return [link.parent for link in job_links] if job_links else []
# _process_job: job_id from URL ("jobid=" param) else f"bdjobs-{hash(job_url)}"
#   company/location/date via class_=lambda c: any(term in (c or "").lower() for term in [...])
# _get_job_details: find div.jobcontent -> h4#job_resp responsibilities heading -> collect following ul/li and p
#   until next h4/h5/hr; else fallback div/section class containing job-description/details/requirements
```

**Flow:** copy `search_params`, set `txtsearch` → loop pages (`pg` param added page>1) → parse `find_job_listings(soup)` (selector ladder → jobdetail-link fallback) → per card `_process_job` (dedupe by id, extract title/company/location/date via class-substring ladders) → `_get_job_details(job_url)` always fetches the detail page (responsibilities-section extraction) → jitter between pages.
**Invariant:** `find_job_listings` tries a list of selectors in order and falls back to `jobdetail` links' parents; `_process_job` extracts company/location/date via `class_=lambda c: any(term in (c or "").lower() ...)` substring ladders (multiple fallback terms); the job id comes from the URL `jobid=` param, else a hash; `_get_job_details` collects responsibilities from `div.jobcontent` following an `h4#job_resp` heading (ul/li and p until the next heading/hr), falling back to a `job-description/details/requirements` class; description is markdown-converted when requested; per-card errors are logged and skipped (not raised).

## Bayt adapter
**Path/Symbol:** `jobspy/bayt/__init__.py:BaytScraper` (22–145) — `scrape` (35–82), `_fetch_jobs` (84–98), `_extract_job_info` (100–137), `_extract_job_url` (139–145).
**Signature:** `BaytScraper.scrape(scraper_input) -> JobResponse`; `_fetch_jobs(query, page) -> list[Tag] | None`; `_extract_job_info(job: Tag) -> JobPost | None`.
**Data Shape:** `base_url="https://www.bayt.com"`; `delay=2`, `band_delay=3`; session created lazily in `scrape` (`create_session(is_tls=False, has_retry=True)`).

### Decisive source
```python
# _fetch_jobs: GET {base}/en/international/jobs/{query}-jobs/?page={page}; soup.find_all("li", attrs={"data-js-job": ""})
# _extract_job_info: h2 (no class) -> title + url; company div.t-nowrap.p10l span; location div.t-mute.t-small
#   job_id = f"bayt-{abs(hash(job_url))}"
# _extract_job_url: a within h2 -> base_url + href.strip()
# scrape loop: while len(job_list) < results_wanted; break if no new jobs on a page (len unchanged)
```

**Flow:** create session lazily → loop pages fetching `li[data-js-job]` cards → `_extract_job_info` (h2 title/link, company span, location div) → append until `results_wanted`; break when a page yields no new jobs (`len(job_list) == initial_count`).
**Invariant:** Bayt pagination stops when a page adds no NEW jobs (not on an empty page); `job_id` is a hash of the URL (`bayt-{abs(hash(job_url))}`); the h2 has no class filter; per-card extraction errors are logged and skipped.
**Probe:** no in-repo test suite; verified against source + `constant.py` (`job_selectors`, `date_formats`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "BDJobs find_job_listings job_selectors BaytScraper _fetch_jobs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the selector-fallback ladder (list of selectors → link-parent fallback), class-substring extraction ladders, responsibilities-section collection, and stop-when-no-new-jobs pagination. Adapt the selectors/class terms to your target markup. Omit the always-fetch-detail-page behavior (BDJobs) if descriptions are optional. Coverage caveat: no in-repo tests; verified against source.
