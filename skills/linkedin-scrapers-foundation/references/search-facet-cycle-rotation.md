<!-- capsule-v2 -->
# Search-facet cycle rotation — how does an infinite re-run loop keep surfacing fresh listings instead of rescraping the same page one?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** with run_non_stop = True, what rotates between cycles so the bot keeps finding new jobs — and where does the rotation arithmetic lie to you?

## alternate_sortby toggle + cycle_date_posted window rotation across run() cycles
**Path/Symbol:** `runAiBot.py:main` (:1174–1186); per-cycle pacing `run` (:1116–1131, two 5-min sleeps between cycles); term shuffle `apply_to_jobs` :848 (`if randomize_search_order: shuffle(search_terms)`); legal facet vocabularies pinned by validator :119–120.
**Signature:** module-global mutation between `run()` calls: `sort_by`, `date_posted`.
**Data Shape:** date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]; sort_by toggles "Most relevant" ↔ "Most recent".

### Decisive source
```python
while(run_non_stop):
    if cycle_date_posted:
        # stop branch: idx+1 > len(options) is UNREACHABLE (max idx+1 == len) → ALWAYS index -1
        date_posted = date_options[idx+1 if idx+1 > len(date_options) else -1] if stop_date_cycle_at_24hr \
                      else date_options[0 if idx+1 >= len(date_options) else idx+1]
    if alternate_sortby:
        sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
        total_runs = run(total_runs)                     # run, then TOGGLE BACK before the next run
        sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
    total_runs = run(total_runs)
    if dailyEasyApplyLimitReached: break
```

**Flow:** each cycle applies the current facets via apply_filters → runs the whole search→apply pass → sleeps ~10 min (two 5-min chunks) → advances the date window (non-stop branch wraps Any time→…→24h→Any time) and/or flips sort order around a dedicated extra run → repeats until the daily Easy Apply latch trips.
**Invariant:** dedupe is NOT the mechanism here — applied_jobs already filters seen IDs; rotation exists to change WHAT LinkedIn serves (recency windows and relevance ordering), because a fixed query returns a stable first page. The daily-limit latch is the only exit.
**Probe:** source-grounded only (orchestrator caveat as recorded in job-run-orchestration); vocabulary pinned by `modules/validator.py:validate_search` (:119–120 check_string option lists). Arithmetic probe executed this pass: for len==4 the stop branch's condition `(idx+1) > 4` is unsatisfiable, so `stop_date_cycle_at_24hr=True` jumps straight to "Past 24 hours" on the FIRST rotation and sticks there — the "advance until 24h then clamp" intent is NOT what ships.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "run_non_stop alternate_sortby date_posted", limit: 6 });
// bm25 ranks shared tokens: returns calculate_date_posted + its tests; main()/run() are read directly at :1116-1186
```

## Verdict
Adopt facet rotation as the freshness mechanism for unattended loops (plus randomize_search_order shuffling), and adopt the toggle-around-a-run pattern so each ordering gets a full cycle. FIX the clamp: implement "advance one step per cycle; stick at last once reached" explicitly instead of the unreachable upper-bound comparison. Adapt windows/vocabularies to your locale UI. Omit the fixed 10-minute sleep shape.
