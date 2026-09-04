<!-- capsule-v2 -->
# LinkedIn guest pagination — cursor ladder, 1000-ceiling, partial-success error policy

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does the LinkedIn adapter page through guest search results and decide when to stop, given no authenticated pagination API?

## Guest-endpoint cursor loop
**Path/Symbol:** `jobspy/linkedin/__init__.py:LinkedIn.scrape` (73–171); class knobs `delay=3`, `band_delay=4`, `jobs_per_page=25` (:49–51); `continue_search` closure (:87–89).
**Signature:** `scrape(scraper_input: ScraperInput) -> JobResponse`. Query params built per iteration: `keywords/location/distance`, `f_WT=2` (remote), `f_JT` single-letter code, `pageNum=0`, `start`, `f_AL=true` (easy apply), `f_C` comma-joined company ids, `f_TPR=r<seconds>` (hours_old×3600).
**Data Shape:** every param whose value is `None` is stripped by `{k: v for k, v in params.items() if v is not None}` (:117) — absent ≠ empty. `start` begins at `(scraper_input.offset // 10 * 10)` (:82).

### Decisive source
```python
continue_search = (
    lambda: len(job_list) < scraper_input.results_wanted and start < 1000
)
while continue_search():
    ...
    response = self.session.get(
        f"{self.base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search?",
        params=params, timeout=10,
    )
    if response.status_code not in range(200, 400):
        log.error(err)                      # 429 gets its own message
        return JobResponse(jobs=job_list)   # PARTIAL SUCCESS: keep what we have
    ...
    job_cards = soup.find_all("div", class_="base-search-card")
    if len(job_cards) == 0:
        return JobResponse(jobs=job_list)   # end-of-results
    ...
    if continue_search():
        time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
        start += len(job_cards)             # NOT a fixed step
```

**Flow:** floor `offset` to a multiple of 10 → loop while under `results_wanted` AND `start < 1000` → GET guest HTML fragment (10 s timeout) → any non-2xx/3xx logs and RETURNS the jobs collected so far → zero cards = natural end → per-card processing (dedupe via `seen_ids`; `job_id = href.split("?")[0].split("-")[-1]`) → inner `break` the moment `continue_search()` goes false → inter-page sleep `uniform(3, 7)` s → advance cursor.
**Invariants:** (1) HARD CEILING `start < 1000` regardless of `results_wanted` — a porter raising `results_wanted` past ~400 silently stalls at 10 pages; (2) PAGE-LEVEL errors return partial `JobResponse` (never raise) — availability beats completeness; (3) CARD-level exceptions DO raise `LinkedInException` (:163–164) — asymmetric policy: transport errors degrade, parse errors kill; (4) cursor advances by `len(job_cards)` not a fixed 10/25 — a short page shifts subsequent alignment relative to the floor-to-10 offset; (5) `jobs_per_page=25` is DECLARED BUT NEVER USED anywhere in the file — dead knob, do not "fix" code that ignores it; (6) `pageNum` stays 0 forever: `start` is the only cursor LinkedIn's guest API honors here.
**Probe:** anchored at the `jobspy/` package root (the dir containing `linkedin/` and `util.py`; all paths below relative to it):
`grep -cF 'jobs-guest/jobs/api/seeMoreJobPostings/search' linkedin/__init__.py` → 1 · `grep -cF 'offset // 10 * 10' linkedin/__init__.py` → 1 · `grep -cF 'start < 1000' linkedin/__init__.py` → 1 · `grep -cF '"pageNum": 0' linkedin/__init__.py` → 1 · `grep -cF 'start += len(job_cards)' linkedin/__init__.py` → 1 · `grep -cF 'random.uniform(self.delay, self.delay + self.band_delay)' linkedin/__init__.py` → 1. All executed green at pin `fda080a`. No in-repo test suite exists — source-verified caveat applies.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "LinkedIn guest seeMoreJobPostings base-search-card scrape", limit: 10 });
```
(live-verified: `JobSpy.jobspy.linkedin.LinkedIn.scrape` ranks 2 of 31, lines 73–171.)

## Verdict
Adopt the ladder: floor-offset → capped loop → per-card dedupe → partial-success returns → variable-step cursor. Adapt delays/user-agent and the 1000 ceiling to your rate-limit budget (the ceiling mirrors LinkedIn's guest hard wall, not taste). Omit `f_TPR`/`f_C` if you don't need freshness or company-id filters — they are plain query params. Coverage caveat: no upstream tests; verified against source at `fda080a`.
