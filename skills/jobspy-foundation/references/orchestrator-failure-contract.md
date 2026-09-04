<!-- capsule-v2 -->
# Orchestrator failure contract — what happens to the other sites when one scraper raises mid-run?

**Source:** JobSpy MIT `main@fda080a373e8`; Codebase Memory `JobSpy`. **Question:** Does scrape_jobs shield one site's failure from the rest, and who owns partial success?

## Registry + unshielded fan-out
**Path/Symbol:** `jobspy/__init__.py:scrape_jobs` — SCRAPER_MAPPING (:58), scrape_site (:104–112), worker (:116–119), submit (:122), as_completed loop (:125–126).
**Signature:** `worker(site) -> (site.value, JobResponse)`; `future.result() -> Tuple[str, JobResponse]`.
**Data Shape:** registry maps every `Site` member to its Scraper class; per-site results land in `site_to_jobs_dict[site.value]` only when their future completes.

### Decisive source
```python
with ThreadPoolExecutor() as executor:
    future_to_site = {executor.submit(worker, site): site for site in scraper_input.site_type}
    for future in as_completed(future_to_site):
        site_value, scraped_data = future.result()   # NO try/except anywhere on this path
# worker -> scrape_site -> scraper_class(proxies=..., ca_cert=..., user_agent=...) -> scraper.scrape(scraper_input)
```

**Flow:** registry lookup (KeyError if a Site member lacks an entry) -> constructor -> scrape() -> future.result() re-raises ANY adapter exception at the as_completed iteration, aborting scrape_jobs before remaining futures are consumed and before any DataFrame is built.
**Invariant:** the orchestrator provides NO failure isolation and no timeout — partial success is an ADAPTER-side obligation. Adapters convert transport errors into logged partial returns (`JobResponse(jobs=job_list)`, e.g. LinkedIn 429 path) but raise typed site exceptions for parse edges; such a raise propagates through the future and kills ALL sites. Porting consequence: wrap future.result() or guarantee adapters never raise, and keep SCRAPER_MAPPING total over Site members.
**Probe:** no in-repo runner (recorded block). Deterministic source evidence: full-range read of __init__.py:31–221 shows zero try/except between result() and scrape(); grep anchors :58/:68/:104/:116/:122/:125/:126 recorded in state.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "JobSpy", function_name: "scrape_jobs", direction: "outbound", depth: 2 });
```

## Verdict
Adopt the registry pattern with a totality check plus explicit per-future exception shielding in your host. Adapt timeout/cancellation policy (JobSpy has none) to your runtime. Omit relying on orchestrator-level isolation that does not exist here. Coverage caveat: behavior derived from source inspection; no test suite pins it.
