<!-- capsule-v2 -->
# ZipRecruiter — mobile-app API with session-event cookie bootstrap, continue-token pagination

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does the ZipRecruiter adapter bootstrap an API session via a device event, paginate with a continue token, and enrich descriptions from the job page?

## ZipRecruiter adapter
**Path/Symbol:** `jobspy/ziprecruiter/__init__.py:ZipRecruiter` (36–219) — `scrape` (57–83), `_find_jobs_in_page` (85–122), `_process_job` (124–177), `_get_descr` (179–212), `_get_cookies` (214–219); `jobspy/ziprecruiter/util.py` — `add_params` (1–23), `get_job_type_enum` (25–31); `jobspy/ziprecruiter/constant.py` (`headers`, `get_cookie_data`).
**Signature:** `ZipRecruiter.scrape(scraper_input) -> JobResponse`; `_find_jobs_in_page(scraper_input, continue_token=None) -> (list[JobPost], next_continue_token)`.
**Data Shape:** `base_url="https://www.ziprecruiter.com"`, `api_url="https://api.ziprecruiter.com"`; `jobs_per_page=20`, `delay=5`; `seen_urls: set`; session created with `create_session(proxies, ca_cert)` (default TLS flavor).

### Decisive source
```python
self.session = create_session(proxies=proxies, ca_cert=ca_cert)
self.session.headers.update(headers)
self._get_cookies()   # POST {api}/jobs-app/event with data=get_cookie_data (device/session properties)
# scrape loop:
max_pages = math.ceil(scraper_input.results_wanted / self.jobs_per_page)
for page in range(1, max_pages + 1):
    if len(job_list) >= results_wanted: break
    if page > 1: time.sleep(self.delay)
    jobs_on_page, continue_token = self._find_jobs_in_page(scraper_input, continue_token)
    if jobs_on_page: job_list.extend(jobs_on_page)
    else: break
    if not continue_token: break
# _find_jobs_in_page: params = add_params(scraper_input); if continue_token: params["continue_from"]=continue_token
#   res = self.session.get(f"{api_url}/jobs-app/jobs", params=params)
#   jobs_list = res_data.get("jobs", []); next_continue_token = res_data.get("continue", None)
#   ThreadPoolExecutor(max_workers=self.jobs_per_page) -> _process_job per job
# _process_job: job_url = f"{base}/jobs//j?lvk={job['listing_key']}"; dedupe by seen_urls
#   comp_interval = "yearly" if comp_interval == "annual" else comp_interval
#   description_full, job_url_direct = self._get_descr(job_url)   # enrich from job page
```

**Flow:** create session → set headers → `_get_cookies()` POSTs a device/session event to the API (bootstrap) → loop pages with `continue_from` token; per page GET `{api}/jobs-app/jobs` with `add_params` (search/location/days/employment_type/zipapply/remote/radius) → thread `_process_job` → extend; stop when no jobs, no continue token, or `results_wanted` reached; slice `[:results_wanted]`.
**Invariant:** pagination is by a `continue` token from the API (not a page counter); `_process_job` dedupes by `job_url`; `compensation_interval` normalizes `"annual"`→`"yearly"`; `_get_descr` enriches description + direct URL from the job page (`div.job_description` + `section.company_description` prettified, and a `script[type=application/json]` `model.saveJobURL` regex `job_url=(.+)`); `date_posted` via `datetime.fromisoformat(posted_time.rstrip("Z"))`; `country` mapped `"US"`→`"usa"` else `"canada"`; transport errors return partial results with an empty continue token.
**Probe:** no in-repo test suite; verified against source + `constant.py` (`headers`, `get_cookie_data`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "ZipRecruiter _find_jobs_in_page add_params continue_from", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the session-event bootstrap, continue-token pagination, and job-page description enrichment. Adapt the API endpoint, headers, and device-event payload per target. Omit the hardcoded iPhone device properties if you don't need them. Coverage caveat: no in-repo tests; verified against source.
