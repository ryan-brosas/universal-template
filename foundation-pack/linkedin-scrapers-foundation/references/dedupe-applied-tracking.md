<!-- capsule-v2 -->
# Dedupe & applied-state tracking — how do I never re-apply to or re-scrape the same item across runs?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550` (`get_applied_job_ids` :163–176 + in-loop guards); LinkedIn-Easy-Apply-Bot Apache-2.0 (`get_appliedIDs` :158–173, timestamp window); EasyApplyJobsBot CC-BY-NC (`linkJobApply` appliedOfferIds sweep :182–195); maximo3k GPL-3 (append-mode CSV with header-on-first-write). Codebase Memory projects of the same names. **Question:** what persistence shape makes cross-run dedupe reliable when the source of truth is a flat file?

## CSV-as-state + pre-click guards
**Path/Symbol:** `runAiBot.py:get_applied_job_ids` (:163–176), guard at :877–881; `easyapplybot.py:get_appliedIDs` (:158–173) with 48-hour window at :167; `linkedin.py:linkJobApply` DOM-sweep variant (:182–195); `prospect_scraper_sales_navigator.py:write_results_to_csv` (:22–29).
**Signature:** `get_applied_job_ids() -> set[str]` — first column of every CSV row; `df[df['timestamp'] > now - timedelta(days=2)]` for time-bounded variants.
**Data Shape:** append-only CSV whose FIRST column is the dedupe key (job ID); writers open in `'a'` mode and emit a header only when `file.tell() == 0` (empty-file probe).

### Decisive source
```python
# load: whole history → set (O(1) membership during the run)
with open(file_name, 'r', encoding='utf-8') as file:
    job_ids.add(row[0])
# save: append-only, header only if truly empty
writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
if csv_file.tell() == 0: writer.writeheader()
# in-loop triple guard before clicking a job:
if job_id in applied_jobs or find_by_class(driver, "jobs-s-apply__application-link", 2):
    continue                      # set-membership AND live-DOM "Applied" badge
```

**Flow:** run start → read CSV into a set → per candidate check set + on-page Applied badge + rejected-set → after success append row immediately (crash-safe: state advances one job at a time).
**Invariant:** three layers — persistent set (cross-run), live DOM badge (same-run external changes), rejected/blacklisted sets (session-local negatives). The EasyApplyJobsBot variant sweeps the listing page for `'Applied'` text BEFORE building its work list so already-applied IDs are filtered without ever opening them. LinkedIn-Easy-Apply-Bot bounds memory with a 2-day timestamp window — port this when IDs churn.
**Probe:** no upstream tests pin the CSV loop — coverage caveat recorded. Adjacent seam that IS tested: `tests/test_helpers.py::test_truncate_for_csv_*` (4 tests) pin safe cell coercion feeding these files; graph resolves both test nodes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "get_applied_job_ids", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "maximo3k-sales-nav-scraper", query: "write_results_to_csv", limit: 5 });
```

## Verdict
Adopt append-only CSV state with tell()==0 headers, first-column key sets, and the layered set+DOM guard; adapt key column, retention window, and storage backend (SQLite/Sheets) to host; omit emoji reporting and donate() nags. Caveat: dedupe loop itself untested upstream; truncation helpers are test-pinned.
