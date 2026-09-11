<!-- capsule-v2 -->
# Google — SERP async-cursor pagination and the fragile nested-JSON job extraction

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does the Google adapter scrape the jobs SERP via an async forward-cursor, and how does it locate job records inside the deeply nested JSON?

## Google adapter
**Path/Symbol:** `jobspy/google/__init__.py:Google` (23–202) — `scrape` (41–84), `_get_initial_cursor_and_jobs` (86–135), `_get_jobs_next_page` (137–140), `_parse_jobs` (142–165), `_parse_job` (167–202); `jobspy/google/util.py` — `find_job_info` (8–23), `find_job_info_initial_page` (26–41); `jobspy/google/constant.py` (`headers_initial`, `headers_jobs`, `async_param`).
**Signature:** `Google.scrape(scraper_input) -> JobResponse`; `_get_initial_cursor_and_jobs() -> (forward_cursor, list[JobPost])`; `_get_jobs_next_page(forward_cursor) -> (list[JobPost], next_cursor)`.
**Data Shape:** `url="https://www.google.com/search"`, `jobs_url="https://www.google.com/async/callback:550"`; `jobs_per_page=10`; `results_wanted` capped at 900; `seen_urls: set`; session `create_session(is_tls=False, has_retry=True)`.

### Decisive source
```python
# Build a natural-language query (search_term + job_type + " near {location}" + time-range + " remote")
#   or use google_search_term verbatim; params = {"q": query, "udm": "8"}
response = self.session.get(self.url, headers=headers_initial, params=params)
pattern_fc = r'<div jsname="Yust4d"[^>]+data-async-fc="([^"]+)"'   # forward cursor
data_async_fc = re.search(pattern_fc, response.text).group(1) if match else None
# _get_jobs_next_page: params = {"fc":[forward_cursor], "fcv":["3"], "async":[async_param]}
#   response = self.session.get(self.jobs_url, headers=headers_jobs, params=params)
# _parse_jobs: start_idx = job_data.find("[[["); end_idx = job_data.rindex("]]]") + 3
#   s = job_data[start_idx:end_idx]; parsed = json.loads(s)[0]
#   for array in parsed: _, job_data = array; if not job_data.startswith("[[["): continue
#       job_d = json.loads(job_data); job_info = find_job_info(job_d)   # recurse for key "520084652"
# _parse_job: job_url = job_info[3][0][0]; title=job_info[0]; company=job_info[1]; location=job_info[2]
#   days_ago_str=job_info[12]; description=job_info[19]; id=f"go-{job_info[28]}"
```

**Flow:** build a natural-language query (or use `google_search_term` verbatim) → GET the SERP with `udm=8` → extract the `data-async-fc` forward cursor + initial jobs via `find_job_info_initial_page` (regex for `520084652":[...]`) → loop `_get_jobs_next_page(forward_cursor)` (async callback with `fc`/`fcv`/`async` params) → `_parse_jobs` slices the `[[[...]]]` JSON and recurses for the `"520084652"` key → `_parse_job` reads positional array indices.
**Invariant:** the forward cursor is a `data-async-fc` attribute (initial page) or `data-async-fc` regex in the callback body; the job records live under the magic key `"520084652"` deep in nested JSON, found by a recursive walk (`find_job_info`); `_parse_job` reads POSITIONAL indices (`job_info[3][0][0]` URL, `[0]` title, `[1]` company, `[2]` location, `[12]` days-ago, `[19]` description, `[28]` id) — extremely brittle to Google layout changes; `days_ago` parsed from a string via `re.search(r"\d+")`; remote inferred inline from description.
**Probe:** no in-repo test suite; the extraction is pinned by `constant.py` (`async_param` is a huge opaque base64-ish blob) and `util.py`. Verified against source. High brittleness caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "Google _parse_jobs find_job_info 520084652 async", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the natural-language-query composition and async forward-cursor pagination pattern. Adapt the magic key `"520084652"` and positional indices to your SERP (they are Google-layout-specific and WILL break on layout change). Omit the brittle positional parsing if you have a structured source. Coverage caveat: no in-repo tests; verified against source; flagged as highly brittle.
