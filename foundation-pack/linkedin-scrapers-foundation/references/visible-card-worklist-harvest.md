<!-- capsule-v2 -->
# Visible-card worklist harvest — how do I build a per-page work list from LinkedIn's virtualized results list when cards only exist in the DOM once scrolled into view?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58b39e2a3bb3f4a2deb1e3c410e7fda7e0e` (`applications_loop` :242–314; wall-clock budget :56–57/:256–258); Codebase Memory `LinkedIn-Easy-Apply-Bot`. **Question:** what is the collect-after-scroll → filter → status-dict → delegate discipline that harvests every rendered card exactly once without missing unmounted ones or reprocessing applied ones?

## Scroll-to-mount, then harvest the visible set
**Path/Symbol:** `easyapplybot.py:EasyApplyBot.applications_loop` (:242–314); scroll kernel `load_page` (:655–667, owned by humanization-scroll); card selector locator `links = '//div[@data-job-id]'` (:133).
**Signature:** `applications_loop(position, location) -> None`; inner state: `count_application/count_job/jobs_per_page` counters, `jobIDs: dict[str, str]` keyed by card id with value 'To be processed'.
**Data Shape:** each card is a `div[data-job-id]` whose `.text` embeds title/company AND the 'Applied' badge when present; `data-job-id` can degenerate to the literal `'search'` when the attribute resolves to the container instead of a job.

### Decisive source
```python
# Selenium only sees RENDERED elements — scroll the container so lazy cards mount first
if self.is_present(self.locator["search"]):
    scrollresults = self.get_elements("search")
    # "Selenium only detects visible elements; if we scroll to the bottom too fast,
    #  only 8-9 results will be loaded into IDs list"  (author comment, :275)
    for i in range(300, 3000, 100):
        self.browser.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollresults[0])
    scrollresults = self.get_elements("search")          # RE-collect after mounting

if self.is_present(self.locator["links"]):
    links = self.get_elements("links")                   # all visible job cards
    jobIDs = {}                                          # {id: processed_status}
    for link in links:
        if 'Applied' not in link.text:                    # badge guard (same-run dedupe)
            if link.text not in self.blacklist:           # text blacklist guard
                jobID = link.get_attribute("data-job-id")
                if jobID == "search":                     # sentinel: not a real job id
                    continue
                jobIDs[jobID] = "To be processed"
    if len(jobIDs) > 0:
        self.apply_loop(jobIDs)                           # delegate BEFORE next page
```

# whole session bounded by wall clock, not counts (:56-57, :256-258)
MAX_SEARCH_TIME = 60 * 60                                # comment says 10h — VALUE is 1h
while time.time() - start_time < self.MAX_SEARCH_TIME:
    log.info(f"{(self.MAX_SEARCH_TIME - (time.time() - start_time)) // 60} minutes left in this search")
```

**Flow:** maximize window → load results page via URL walk → stepped container scroll (300→3000 px by 100) so virtualized cards mount → RE-query the card list AFTER scrolling → filter by Applied-badge text, blacklist text, and the data-job-id=='search' sentinel → accumulate {jobID: status} dict → hand the WHOLE page batch to apply_loop → advance to next page → repeat until the session time budget expires.
**Invariant:** the work list is built ONLY from a post-scroll re-query — harvesting before the scroll ladder yields the first 8–9 mounted cards and silently skips the rest; the three filters (badge, blacklist, id-sentinel) run at COLLECTION time so delegated workers never see skipped candidates. Honest caveats inherited here (both verified at HEAD 8471c58): (1) the threaded `jobs_per_page` offset has NO increment site anywhere (:246/:253/:302/:307/:690), so this loop revisits `start=0` every cycle; (2) the status channel is WRITE-DEAD — `apply_loop` consumes `'To be processed'` (:317) but its final statement is the comparison `jobIDs[jobID] == applied` (:323), never an assignment, so seeded statuses stay frozen forever. With neither pagination NOR the status dict advancing, cross-cycle and within-run non-reprocessing rest entirely on the badge guard + persistent out.csv dedupe (dedupe-applied-tracking), NOT on either progress mechanism. Porters must add a real offset increment AND fix the status write (`=`, not `==`) or an explicit page-termination signal.
**Probe:** repo ships no test suite — coverage caveat recorded. Deterministic probes verified byte-for-byte at HEAD 8471c58: `grep -n "range(300, 3000, 100)" easyapplybot.py` ⇒ :276 (single stepped-ladder site); `grep -n "data-job-id" easyapplybot.py` ⇒ :133/:294 (+ commented :285); `grep -n "To be processed\|== applied" easyapplybot.py` ⇒ :299 seed / :317 consume-compare / :323 dead status write; `grep -n MAX_SEARCH_TIME easyapplybot.py` ⇒ :56/:57/:256/:258 (budget + remaining-minutes log line).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", query: "applications_loop jobIDs links applied", limit: 5 });
// ⇒ EasyApplyBot.applications_loop :242-314 (resolved live this pass)
await mcp.codebase_memory.trace_path({ project: "LinkedIn-Easy-Apply-Bot", function_name: "applications_loop", direction: "outbound", depth: 2 });
// ⇒ 11 callees: apply_loop, apply_to_job, get_elements, is_present, load_page, next_jobs_page …
```

## Verdict
Adopt post-scroll re-collection, collection-time triple filtering, batch delegation, and the wall-clock session budget with a remaining-time log line; adapt scroll bounds (3000 px cap is arbitrary — derive from container scrollHeight) and fix BOTH progress mechanisms this loop lacks — increment `start` by the page size (or read LinkedIn's paging metadata) AND make apply_loop actually write the status (`jobIDs[jobID] = applied`, not `==`); omit the bare `except Exception: print(e)` island around the whole iteration (string-outcome-channel shows the narrower per-job placement) and do not copy the dead `count_application/count_job` counters. Contrast: humanization-scroll owns the SCROLL mechanics themselves; this seam owns what you do AFTER the scroll — building a trustworthy work list from a lazily-mounted DOM.
