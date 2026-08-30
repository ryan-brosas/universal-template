<!-- capsule-v2 -->
# Scrape() orchestration template — what fixed ceremony does every page scraper share, and where should a missing value become None versus a sentinel string?

**Source:** linkedin_scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (≡ joeyism-linkedin-scraper identical tree); Codebase Memory `linkedin_scraper`. **Question:** what is the common run-shape of JobScraper.scrape / CompanyScraper.scrape / PersonScraper.scrape, and how does each policy differ on failure?

## One ceremony, three degradation policies
**Path/Symbol:** `linkedin_scraper/scrapers/job.py:JobScraper.scrape` (:39–100), `linkedin_scraper/scrapers/company.py:CompanyScraper.scrape` (:39–85), `linkedin_scraper/scrapers/person.py:PersonScraper.scrape` (:29–110); shared guards from `scrapers/base.py` (navigate_and_wait / ensure_logged_in / check_rate_limit — mechanics owned by scraper-base-callbacks).
**Signature:** all three: `async scrape(linkedin_url) -> <Model>` with `callback.on_start(type, url)` first and `on_complete(type, model)` last.
**Data Shape:** constructor contract `(page, callback=None)` defaulting to SilentCallback — scrapers are usable bare but observable when composed.

### Decisive source
```python
await self.callback.on_start("company", linkedin_url)
await self.navigate_and_wait(linkedin_url)     # 10%
await self.check_rate_limit()                  # typed RateLimitError escapes here
name = await self._get_name()                  # field islands degrade, never raise
overview = await self._get_overview()
company = Company(linkedin_url=linkedin_url, name=name,
                  about_us=about_us, **overview)   # dict-splat assembly
await self.callback.on_progress("Scraping complete", 100)
await self.callback.on_complete("company", company)
```

**Flow:** identical ceremony — on_start → navigate_and_wait → check_rate_limit → ordered field getters with progress milestones between each → pydantic model constructed ONCE at the end → on_progress(…,100) → on_complete → return model. Differences are POLICY, not shape: person navigates before ensure_logged_in and wraps its whole body in try/except → ScrapingError; job/company let guard exceptions propagate untyped-wrapped; company assembles nested data by splatting ONE overview dict (`**overview`) into the model so _get_overview owns every optional scalar.
**Invariant:** the identity URL argument is passed through VERBATIM into the model (the model's validator re-checks it); progress milestones are monotonic and end at exactly 100 only after the model exists; a scrape either returns a constructed model or raises BEFORE construction — it never returns half-populated dicts. Degradation matrix: missing NAME → sentinel strings ("Unknown" person :115/:122, "Unknown Company" company :87–96) because downstream display joins need a non-empty label; missing EVERYTHING ELSE → None fields (models tolerate all-None except the validated URL).
**Probe:** deterministic: unit lane green at this pin (`pytest -m unit`, incl. test_job_model_to_dict/to_json + person/company model tests); source needles: `**overview` at company.py :74–79, "Unknown Company" at :96, blanket wrap at person.py :108–110. Integration behavior session-gated as recorded in credential-free-test-ladder.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin_scraper", name_pattern: "^scrape$", label: "Method", format: "tree", limit: 20 });
```

## Verdict
Adopt: the five-beat ceremony (announce → navigate → throttle-gate → islanded getters → construct-once) and the sentinel-for-identity vs None-for-content rule; keep the callback channel optional-by-default so composition stays cheap. Adapt milestone percentages per host. Omit the blanket ScrapingError re-wrap unless your callers genuinely cannot catch the root class (see exception-taxonomy-wiring). Coverage caveat: orchestration bodies have no unit tests (integration-only); evidence is whole-file reads of job.py/company.py/person.py at the cited pin plus graph enumerations.
