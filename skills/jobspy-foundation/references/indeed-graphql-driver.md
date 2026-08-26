<!-- capsule-v2 -->
# Indeed — GraphQL cursor pagination, composite filters, and the employer-dossier enrichment

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does the Indeed adapter drive a GraphQL API with cursor pagination and composite filters, and how does it enrich company data from the employer dossier?

## Indeed GraphQL driver
**Path/Symbol:** `jobspy/indeed/__init__.py:Indeed` (29–260) — `scrape` (50–81), `_scrape_page` (83–135), `_build_filters` (137–193), `_process_job` (195–260); `jobspy/indeed/constant.py:job_search_query` (1–98), `api_headers` (100–109); `jobspy/indeed/util.py` — `get_job_type` (5–17), `get_compensation` (20–49), `get_compensation_interval` (71–83), `is_job_remote` (52–68).
**Signature:** `Indeed.scrape(scraper_input) -> JobResponse`; `_scrape_page(cursor) -> (list[JobPost], next_cursor)`; `_build_filters() -> str` (GraphQL fragment).
**Data Shape:** `api_url = "https://apis.indeed.com/graphql"`; `jobs_per_page=100`; `num_workers=10`; `seen_urls: set`; per-country `base_url = f"https://{domain}.indeed.com"` and `indeed-co` header from `Country.indeed_domain_value`.

### Decisive source
```python
domain, self.api_country_code = self.scraper_input.country.indeed_domain_value
self.base_url = f"https://{domain}.indeed.com"
self.headers["indeed-co"] = self.scraper_input.country.indeed_domain_value
# ...
while len(self.seen_urls) < scraper_input.results_wanted + scraper_input.offset:
    jobs, cursor = self._scrape_page(cursor)
    if not jobs: break
    job_list += jobs
return JobResponse(jobs=job_list[offset : offset + results_wanted])
# _scrape_page: query = job_search_query.format(what=..., location=..., dateOnIndeed=..., cursor=..., filters=...)
#   payload = {"query": query}; POST api_url with api_headers_temp["indeed-co"]=api_country_code, verify=False
#   new_cursor = data["data"]["jobSearch"]["pageInfo"]["nextCursor"]
# _build_filters: hours_old -> date filter; easy_apply -> keyword indeedApplyScope DESKTOP;
#   job_type/is_remote -> composite keyword attributes keys ["CF3CP","75GKK","NJXCK","VDTG7","DSQF7"]
```

**Flow:** resolve country → domain + API code; loop `_scrape_page(cursor)` until `seen_urls` reaches `results_wanted + offset`; each page POSTs a GraphQL query (filters injected as a formatted fragment — `dateOnIndeed` when `hours_old`, `indeedApplyScope:DESKTOP` when `easy_apply`, or a `composite` keyword-attributes filter for job_type/remote keys); parse `jobSearch.results[].job`; cursor from `pageInfo.nextCursor`; slice `[offset:offset+results_wanted]`.
**Invariant:** pagination is by `seen_urls` count (dedupe drives the loop), NOT page count; the search term is escaped (`replace('"', '\\"')`); `verify=False` on the POST; the `indeed-co` header carries the API country code; `_build_filters` is mutually exclusive — `hours_old` short-circuits the composite filter (the docstring notes "if hours_old is provided, composite filter for job_type/is_remote is not possible"). `_process_job` dedupes by `job_url` (`{base_url}/viewjob?jk={key}`), parses `datePublished` ms→`%Y-%m-%d`, and enriches company data from the `employer.dossier` (industry code cleaned by stripping `Iv1`/`_` and title-casing; `employeesLocalizedLabel`, `revenueLocalizedLabel`, `briefDescription`, `squareLogoUrl`, `corporateWebsite`).
**Probe:** no in-repo test suite; the GraphQL shape is pinned by `job_search_query` in `constant.py`. Verified against source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "Indeed _scrape_page job_search_query _build_filters", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt GraphQL cursor pagination driven by a dedupe-set count, formatted filter fragments, and employer-dossier enrichment. Adapt the GraphQL query/filter keys and country routing to your target. Omit `verify=False` in production TLS contexts. Coverage caveat: no in-repo tests; verified against source.
