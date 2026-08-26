<!-- capsule-v2 -->
# Orchestrator — how multi-site results are flattened, deduped and column-normalized

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does `scrape_jobs` turn N per-site `JobResponse`s into one sorted, column-stable DataFrame without losing site identity?

## Orchestrator flatten path
**Path/Symbol:** `jobspy/__init__.py:scrape_jobs` (31–221), `worker` (116–119), `scrape_site` (104–112).
**Signature:** `scrape_jobs(site_name, search_term, google_search_term, location, distance=50, is_remote=False, job_type, easy_apply, results_wanted=15, country_indeed="usa", proxies, ca_cert, description_format="markdown", linkedin_fetch_description=False, linkedin_company_ids, offset=0, hours_old, enforce_annual_salary=False, verbose=0, user_agent, **kwargs) -> pd.DataFrame`.
**Data Shape:** input is a `ScraperInput` (built inside); output is a single wide DataFrame whose columns follow the fixed `desired_order` list, rows sorted by `(site asc, date_posted desc)`, all-NA columns dropped.

### Decisive source
```python
with ThreadPoolExecutor() as executor:
    future_to_site = {executor.submit(worker, site): site for site in scraper_input.site_type}
    for future in as_completed(future_to_site):
        site_value, scraped_data = future.result()
        site_to_jobs_dict[site_value] = scraped_data
# per job: job_data = job.dict(); job_data["site"] = site  (site.value, e.g. "linkedin")
# compensation dict -> interval/min_amount/max_amount/currency + salary_source
# enforce_annual_salary -> convert_to_annual(job_data)
filtered_dfs = [df.dropna(axis=1, how="all") for df in jobs_dfs]   # drop all-NA cols per site
jobs_df = pd.concat(filtered_dfs, ignore_index=True)
for column in desired_order:
    if column not in jobs_df.columns:
        jobs_df[column] = None                                     # backfill missing cols
jobs_df = jobs_df[desired_order]
return jobs_df.sort_values(by=["site", "date_posted"], ascending=[True, False]).reset_index(drop=True)
```

**Flow:** normalize `site_name` (str/Site/list → list[Site] via `map_str_to_site`) → build one `ScraperInput` → submit one `worker` per site to a `ThreadPoolExecutor` → collect `{site.value: JobResponse}` as futures complete → flatten every `JobPost.dict()` into a row, injecting `site`, renaming `company_name→company`, joining `job_type`/`emails`/`skills` lists with `", "`, and expanding the `compensation` dict into flat columns → concat → drop all-NA columns → backfill `desired_order` → sort.
**Invariant:** the `site` column carries `Site.value` (lowercase, e.g. `"linkedin"`, `"zip_recruiter"`), NOT the display name — display capitalization (`"LinkedIn"`, `"ZipRecruiter"`) is only used in the log line. `results_wanted` is honored per-site by each scraper, not re-sliced here. `salary_source` is set to `DIRECT_DATA` when a structured `compensation` exists, else (USA only) derived from the description via `extract_salary` with `DESCRIPTION` provenance; it is nulled when no `min_amount` is present.
**Probe:** no test suite ships in-repo (README documents the DataFrame output shape: `SITE/TITLE/COMPANY/CITY/STATE/JOB_TYPE/INTERVAL/MIN_AMOUNT/MAX_AMOUNT/JOB_URL/DESCRIPTION`). Behavioral contract: concurrent per-site execution, one `site` value per row, fixed column order, `(site, date_posted)` sort.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "scrape_jobs flatten DataFrame desired_order", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flatten-and-normalize pipeline (per-site all-NA column drop, `desired_order` backfill, `(site, date_posted)` sort, `", ".join` list flattening). Adapt `enforce_annual_salary`/description-based salary fallback to your locale (the description fallback only runs for `Country.USA`). Omit the pandas DataFrame output if your host returns JSON/objects — the normalization rules (list-join, dict-expand, column backfill) still apply. Coverage caveat: no in-repo test suite; verified against source + README.
