<!-- capsule-v2 -->
# Paging base URL accumulation — what silently happens when a page loop appends `&start=` to the SAME binding it is iterating instead of rebuilding from an immutable base?

**Source:** EasyApplyJobsBot CC-BY-NC 4.0 `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** does this bot's per-page offset arithmetic actually paginate, and what must a porter change to make it honest?

## The increment site exists, but it composes onto a mutating base — offsets ACCUMULATE
**Path/Symbol:** `linkedin.py:linkJobApply` page loop (:160–164); count math feeding `totalPages` owned by displayed-count-page-budget.
**Signature:** inline in nested loop: `for page in range(totalPages): currentPageJobs = constants.jobsPerPage * page; url = url + "&start=" + str(currentPageJobs)`.
**Data Shape:** `jobsPerPage = 25` (constants.py :8); `url` is ALSO the outer loop variable bound by `for url in urlData:` (:139).

### Decisive source
```python
for url in urlData:                     # outer: one search URL per config pair
    ...
    for page in range(totalPages):
        currentPageJobs = constants.jobsPerPage * page
        url = url + "&start=" + str(currentPageJobs)   # ⚠️ reassigns the OUTER binding
        self.driver.get(url)
```

**Flow (executed table, exact statement semantics, this pass):**
| page | URL sent | `&start=` occurrences |
|---|---|---|
| 0 | `…?f_AL=true&keywords=frontend&start=0` | 1 |
| 1 | `…&start=0&start=25` | 2 |
| 2 | `…&start=0&start=25&start=50` | 3 |

**Invariant:** the base URL is never rebuilt, so every page after 0 carries ALL prior offsets as duplicate query keys. Pagination correctness now rides entirely on which occurrence the server honors: first-wins parsing pins every fetch to page 0 (silent infinite re-scrape of the same listings while counters and caps still advance), last-wins advances correctly by accident. Either way the emitted URL grammar is wrong and untestable. Fix shape for ports: keep the template immutable (`base = url` before the loop; `driver.get(f"{base}&start={25*page}")`). Sibling trap contrast: visible-card-worklist-harvest (LinkedIn-Easy-Apply-Bot) documents the opposite defect — a `start=` parameter with NO increment site at all; this repo HAS the increment site but composes onto a mutating string.
**Probe:** repo ships no tests (standing caveat). Executed byte-for-byte at HEAD: `grep -n '&start=' linkedin.py constants.py` ⇒ exactly linkedin.py :162 + constants.py :21 (a dev fixture that builds `testPageUrl` correctly ONCE); live python execution of the exact composition statements produced the three-row table above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "linkJobApply page start jobsPerPage", limit: 5 });
// ⇒ EasyApplyJobsBot.linkedin.Linkedin.linkJobApply Method linkedin.py 127-299
```

## Verdict
Adopt the invariant, not the code: paging URLs are derived values — always rebuild from an immutable base per page index; never mutate the value you are iterating. Adapt offset math to the surface's real page size (this repo's 25 matches jobs search; Sales Nav differs). Omit duplicate query keys entirely — even when a target server tolerates them today, first-vs-last-wins is undocumented and rot-prone. Cross-refs: displayed-count-page-budget owns how totalPages was computed; harvest within each page is owned by stale-proof-two-pass-harvest.
