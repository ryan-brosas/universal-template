<!-- capsule-v2 -->
# Naukri — placeholder-driven location/salary parsing and Indian salary-unit (Lakh/Crore) conversion

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does the Naukri adapter parse location and salary from typed `placeholders`, convert Indian salary units (Lakhs/Crores), and infer work-from-home type?

## Naukri adapter
**Path/Symbol:** `jobspy/naukri/__init__.py:Naukri` (40–304) — `scrape` (66–150), `_process_job` (152–211), `_get_location` (213–227), `_get_compensation` (229–264), `_parse_date` (266–291), `_infer_work_from_home_type` (293–303); `jobspy/naukri/util.py` — `parse_job_type` (8–18), `parse_company_industry` (21–28), `is_job_remote` (31–37); `jobspy/naukri/constant.py` (`headers`).
**Signature:** `Naukri.scrape(scraper_input) -> JobResponse`; `_get_location(placeholders) -> Location`; `_get_compensation(placeholders) -> Compensation | None`; `_parse_date(label, created_date) -> date | None`.
**Data Shape:** `base_url="https://www.naukri.com/jobapi/v3/search"`; `jobs_per_page=20`; `delay=3`, `band_delay=4`; `seen_ids: set`; session `create_session(is_tls=False, has_retry=True, delay=5, clear_cookies=True)`.

### Decisive source
```python
# _get_location: placeholders with type=="location" -> label "city, state"
for placeholder in placeholders:
    if placeholder.get("type") == "location":
        parts = placeholder.get("label", "").split(", ")
        location = Location(city=parts[0], state=parts[1] if len(parts) > 1 else None, country=Country.INDIA)
# _get_compensation: placeholders with type=="salary"; "Not disclosed" -> None
salary_match = re.match(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(Lacs|Lakh|Cr)\s*(P\.A\.)?", salary_text, re.IGNORECASE)
if salary_match:
    min_salary, max_salary, unit = salary_match.groups()[:3]
    if unit.lower() in ("lacs", "lakh"): min_salary *= 100000; max_salary *= 100000   # 1 Lakh = 100,000 INR
    elif unit.lower() == "cr": min_salary *= 10000000; max_salary *= 10000000          # 1 Crore = 10,000,000 INR
    return Compensation(min_amount=int(min_salary), max_amount=int(max_salary), currency="INR")
# _infer_work_from_home_type: "hybrid" -> Hybrid; "remote" -> Remote; else "Work from office"
# _parse_date: "today"/"just now"/"few hours" -> today; "N days ago" -> today - N days; else created_date ms timestamp
```

**Flow:** build params (noOfResults/urlType/searchType/keyword/pageNo/k/seoKey/src/latLong/location/remote, `days=seconds_old//86400` when `hours_old`) → GET the v3 search API → parse `data.jobDetails` → per job `_process_job`: `_get_location`/`_get_compensation` from typed `placeholders`, `_parse_date` from `footerPlaceholderLabel`/`createdDate`, optional full description (gated by `linkedin_fetch_description`), Naukri-specific fields (`skills` from `tagsAndSkills`, `experience_range` from `experienceText`, `company_rating`/`reviews_count` from `ambitionBoxData`, `vacancy_count`, `work_from_home_type`).
**Invariant:** location and salary come from TYPED `placeholders` (`type=="location"`, `type=="salary"`), not free text; Indian salary units are converted to absolute INR (Lakh ×100,000, Crore ×10,000,000); `"Not disclosed"` salary → `None`; `_parse_date` prefers the human label, falls back to the `createdDate` ms timestamp; `_infer_work_from_home_type` checks location label + title + description for hybrid/remote and defaults to `"Work from office"`; per-job parse errors RAISE `NaukriException` while transport errors return partial results; `continue_search` caps at `page <= 50` (arbitrary limit).
**Probe:** no in-repo test suite; verified against source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "Naukri _get_compensation placeholders Lakh Crore", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt typed-placeholder parsing (location/salary by `type`), Indian salary-unit conversion, and work-from-home inference. Adapt the placeholder schema and date-label formats per target. Omit the Naukri-specific `skills`/`experience_range`/`ambitionBoxData` fields if not needed. Coverage caveat: no in-repo tests; verified against source.
