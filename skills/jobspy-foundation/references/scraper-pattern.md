<!-- capsule-v2 -->
# Per-site scraper pattern — guest endpoints, pagination ceilings, dedupe, jitter, partial-success, auth-wall detection

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** What is the copy-this-site recipe for adding a new job-board scraper, and what invariants a porter would get wrong (pagination ceiling, partial success, auth-wall-as-data)?

## Package shape & the real scraper
**Path/Symbol:** `jobspy/linkedin/__init__.py:LinkedIn` (47–345) as the canonical adapter; package shape per site is `__init__.py` (Scraper subclass) + `constant.py` (headers) + `util.py` (site parsers). See also `jobspy/exception.py` (per-site exceptions: `LinkedInException`, `IndeedException`, `ZipRecruiterException`, `GlassdoorException`, `GoogleJobsException`, `BaytException`, `NaukriException`, `BDJobsException`).
**Signature:** `LinkedIn.scrape(self, scraper_input) -> JobResponse` (73–171); `_process_job` (173–247); `_get_job_details` (249–302); `_get_location` (304–328); `_parse_job_url_direct` (330–345).
**Data Shape:** class attrs `base_url`, `delay=3`, `band_delay=4`, `jobs_per_page=25`; `seen_ids: set[str]`; `start` pagination cursor.

### Decisive source
```python
# Guest API, not pages:
response = self.session.get(f"{self.base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search?", params=params, timeout=10)
# Hard pagination ceiling + offset normalization:
start = scraper_input.offset // 10 * 10 if scraper_input.offset else 0
continue_search = lambda: len(job_list) < scraper_input.results_wanted and start < 1000
# Dedupe across pages (sites reshuffle between pages):
if job_id in seen_ids: continue
seen_ids.add(job_id)
# Politeness jitter BETWEEN pages only:
if continue_search():
    time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
    start += len(job_cards)
# Partial success on transport errors (429 keeps pages 1-4):
if response.status_code == 429: err = "429 Response - Blocked by LinkedIn for too many requests"
else: err = f"LinkedIn response status code {response.status_code} - {response.text}"
log.error(err); return JobResponse(jobs=job_list)
# Auth-wall is DATA, not an exception:
if "linkedin.com/signup" in response.url: return {}
# Direct apply URL hidden in <code id="applyUrl">:
self.job_url_direct_regex = re.compile(r'(?<=\?url=)[^"]+')
```

**Flow:** build params (keywords/location/distance/f_WT/f_JT/pageNum/start/f_AL/f_C, plus `f_TPR=r{seconds}` when `hours_old`) → GET the guest fragment endpoint → parse `div.base-search-card` cards → dedupe by id → optionally fetch full descriptions (gated by `linkedin_fetch_description`, one request each) → jitter between pages → return `job_list[:results_wanted]`.
**Invariant:** the loop caps at `start < 1000` (site-enforced ceiling); incoming `offset` is normalized to page boundaries (`offset // 10 * 10`); dedupe across pages because sites reshuffle; per-card parse errors RAISE the site exception (`LinkedInException`) while transport errors RETURN partial results; empty card page = natural end (distinct from an error); expensive description fields are opt-in and `results_wanted` is honored strictly (`job_list[:results_wanted]``); auth-wall redirects are detected via `response.url` and skipped, not raised.
**Probe:** no in-repo test suite. Behavioral contract: typed `JobResponse` returned; `results_wanted` honored exactly; second run dedupes; 429 mid-pagination preserves earlier pages; description format matches `DescriptionFormat`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "LinkedIn scrape jobs-guest seeMoreJobPostings", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-site package shape (`__init__.py` + `constant.py` + `util.py`), guest-endpoint-first strategy, hard pagination ceiling, cross-page dedupe, jitter delays, partial-success-on-transport-error, auth-wall-as-data, and opt-in expensive fields. Adapt selectors, params, and retry budgets per site. Omit the LinkedIn-specific guest URL and auth-wall needle for other sites. Coverage caveat: no in-repo tests; verified against source.
