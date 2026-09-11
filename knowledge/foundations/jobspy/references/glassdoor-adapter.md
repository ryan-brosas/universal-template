<!-- capsule-v2 -->
# Glassdoor — CSRF-token bootstrap, location resolution, threaded per-job description fetch

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does the Glassdoor adapter bootstrap a CSRF token, resolve a location to an id/type, and fetch per-job descriptions concurrently?

## Glassdoor adapter
**Path/Symbol:** `jobspy/glassdoor/__init__.py:Glassdoor` (35–322) — `scrape` (53–97), `_fetch_jobs_page` (99–150), `_get_csrf_token` (152–162), `_process_job` (164–218), `_fetch_job_description` (220–256), `_get_location` (258–284), `_add_payload` (286–322); `jobspy/glassdoor/util.py` — `parse_compensation` (4–23), `parse_location` (32–36), `get_cursor_for_page` (39–41); `jobspy/glassdoor/constant.py` (`headers`, `query_template`, `fallback_token`).
**Signature:** `Glassdoor.scrape(scraper_input) -> JobResponse`; `_fetch_jobs_page(location_id, location_type, page_num, cursor) -> (list[JobPost], cursor)`.
**Data Shape:** `jobs_per_page=30`, `max_pages=30`, `results_wanted` capped at 900; `seen_urls: set`; `base_url` from `Country.get_glassdoor_url()`; CSRF token fetched from a generic page or falls back to `fallback_token`.

### Decisive source
```python
self.base_url = self.scraper_input.country.get_glassdoor_url()
self.session = create_session(proxies=self.proxies, ca_cert=self.ca_cert, has_retry=True)
token = self._get_csrf_token()          # GET {base}/Job/computer-science-jobs.htm, regex r'"token":\s*"([^"]+)"'
headers["gd-csrf-token"] = token if token else fallback_token
location_id, location_type = self._get_location(scraper_input.location, scraper_input.is_remote)
if location_type is None: return JobResponse(jobs=[])     # 429 -> None,None -> empty result
# _fetch_jobs_page: POST {base}/graph with data=payload (json.dumps([payload])), timeout_seconds=15
#   res_json = response.json()[0]; if "errors" in res_json: raise ValueError
#   ThreadPoolExecutor(max_workers=self.jobs_per_page) -> _process_job per job
#   cursor = get_cursor_for_page(res_json["data"]["jobListings"]["paginationCursors"], page_num + 1)
# _get_location: no location/is_remote -> ("11047","STATE") remote options; else findPopularLocationAjax.htm
#   locationType C->CITY, S->STATE, N->COUNTRY; 429 -> (None,None)
# _add_payload: fromage = max(hours_old//24, 1); filterParams easy_apply(applicationType=1), fromAge, jobType
```

**Flow:** resolve country → glassdoor URL → create session (has_retry) → fetch CSRF token (fallback if absent) → resolve location to `(id, type)` (remote short-circuits to a fixed `("11047","STATE")`) → loop pages `range(range_start, range_end)` where `range_start = 1 + offset//jobs_per_page` and `range_end = min(tot_pages, max_pages+1)` → per page POST the GraphQL search payload → thread each job through `_process_job` → extend + slice to `results_wanted`.
**Invariant:** `_process_job` dedupes by `job_url` (`{base}/job-listing/j?jl={id}`); `locationType=="S"` means remote (`is_remote=True`, no `Location`); `ageInDays` → `date_posted` via `datetime.now() - timedelta(days=age_in_days)`; per-job descriptions are fetched CONCURRENTLY via `ThreadPoolExecutor` (each a separate `requests.post` to `{base}/graph` with `JobDetailQuery`); `parse_compensation` uses `payPeriod` + `payPeriodAdjustedPay` p10/p90 percentiles (annualized by `CompensationInterval.get_interval`); a non-200 or `"errors"` in the response raises/returns empty, not a crash.
**Probe:** no in-repo test suite; verified against source + `constant.py` (`query_template`, `fallback_token`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "Glassdoor _get_csrf_token _get_location _fetch_jobs_page", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt CSRF-token bootstrap with fallback, location→id/type resolution (remote short-circuit), and threaded per-job description fetch. Adapt the GraphQL query, location AJAX endpoint, and token regex per site. Omit the hardcoded `("11047","STATE")` remote location if your target differs. Coverage caveat: no in-repo tests; verified against source.
