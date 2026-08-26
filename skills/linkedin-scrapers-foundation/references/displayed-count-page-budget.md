<!-- capsule-v2 -->
# Displayed-count page budget — how do you turn LinkedIn's "1,234 jobs" label into a bounded number of result pages?

**Source:** EasyApplyJobsBot CC BY-NC-SA 4.0 (learn-only: patterns + control flow, zero verbatim reuse) `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** how does a DOM-label count become pages without trusting it unbounded?

## jobsToPages ceil÷25 with a hard 40-page wall
**Path/Symbol:** `utils.py:jobsToPages` (:75–88); honest-skip reverse-parse `utils.py:urlToKeywords` (:90–95); caller `linkedin.py:linkJobApply` (:146–159).
**Signature:** `jobsToPages(numOfJobs: str) -> int`; `urlToKeywords(url: str) -> List[str] -> [keyword, location]`.
**Data Shape:** input = raw `//small` display text ("1,234 jobs") OR a bare int string; output = page count; `constants.jobsPerPage = 25`.

### Decisive source
```python
if (' ' in numOfJobs):
    spaceIndex = numOfJobs.index(' ')
    totalJobs = (numOfJobs[0:spaceIndex])
    totalJobs_int = int(totalJobs.replace(',', ''))
    number_of_pages = math.ceil(totalJobs_int/constants.jobsPerPage)
    if (number_of_pages > 40 ): number_of_pages = 40
else:
    number_of_pages = int(numOfJobs)
return number_of_pages
```

**Flow:** missing `//small` element ⇒ caller catches, `urlToKeywords` reverse-parses keywords/location out of the URL for an honest skip log line, then `continue`; else first space-token → comma-strip → ceil(÷25) → cap 40 (=1000-job wall); bare-int branch trusts the string directly.
**Invariant:** the wall guards ONLY the spaced/display branch — the bare-int branch is UNCAPPED (cap both when porting). Malformed text raises ValueError from a call site that is NOT inside try (`linkJobApply` guards only the //small read) and kills the run.
**Probe:** real-exec of the repo's own function bytes (exec'd segment of utils.py): `j2p("1,234 jobs")=40`, `j2p("25 jobs")=1`, `j2p("26 jobs")=2`, `j2p("40001 jobs")=40`, `j2p("garbage") raises ValueError`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "jobsToPages urlToKeywords getUrlDataFile", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "EasyApplyJobsBot", qualified_name: "EasyApplyJobsBot.utils.jobsToPages" });
```

## Verdict
Adopt: ceil÷page-size + explicit wall + empty-search skip labeled from the URL itself. Adapt: wrap the parse in the caller, cap both branches, tolerate locale count formats. Omit: nothing structural. Contrast `voyager-pagination` (API-side remainder-shrunk counts, same ~1000-result wall) — this is the DOM-label variant. Coverage caveat: no upstream tests; behavior pinned by the executed real-code probe above plus graph parity.