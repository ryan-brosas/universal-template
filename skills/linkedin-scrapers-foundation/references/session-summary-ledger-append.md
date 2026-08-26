<!-- capsule-v2 -->
# Session-summary ledger append — how do I write a human-readable end-of-run summary without corrupting the machine ledger?

**Source:** EasyApplyJobsBot CC-BY-NC `main@70fe7484` — patterns only; Codebase Memory `EasyApplyJobsBot`. **Question:** where does the session summary go, and what file protocol keeps it coexisting with the per-application rewrite-on-write ledger?

## The summary writer
**Path/Symbol:** `utils.py:printSessionSummary` (:125–161); companion `writeResults` (:97–119) already covered by ledger-contrast-csv-vs-summary; counters fed by `easyapplybot.py` string-outcome-channel tallies.
**Signature:** `printSessionSummary(count_jobs, count_applied, count_blacklisted, count_already_applied, count_cannot_apply, duration_sec)` → console block (emoji table, duration rounded to 0.1 min) + ONE appended `"---- Session Summary ----"` line in the SAME dated file.
**Data Shape:** appends to `"data/Applied Jobs DATA - %Y%m%d.txt"` — identical daily filename as writeResults; summary is a single `\n`-joined multi-line block guarded by its own `----` banner.

### Decisive source
```python
summary_lines = ["", "---- Session Summary ----",
    f"Jobs processed: {count_jobs} | Applied: {count_applied} | ... | Duration: {duration_min} min"]
with open(file_path, "a", encoding="utf-8") as f:      # APPEND, never read-modify-write
    f.write("\n".join(summary_lines) + "\n")
```

**Flow:** run ends → console summary prints → append-mode write of one banner-delimited block to the day's file. Contrast with writeResults' per-application path: that one READS all lines, strips old `----` banners, rewrites header+history+new row (rewrite-on-write); the summary path NEVER reads, so the two writers cannot clobber each other's content.
**Invariant:** banner (`----`) lines are the parse boundary — writeResults STRIPS them on rewrite and re-emits its own header, which is exactly why summaries must be banner-delimited: they are stripped from the numbered history on the next application yet survive for humans reading the file. Append-only failure mode is silent loss at worst (wrapped try/except printing a truncated error), never ledger corruption.
**Probe:** source-grounded (no tests in repo): needle `Session Summary` + `open(file_path, "a"` in `utils.py`; line-range anchor :125/:152–160. Graph probe resolves printSessionSummary.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "printSessionSummary writeResults", limit: 10 });
```

## Verdict
Adopt: same-file dual-writer split (append-banner for summaries vs rewrite-strip for rows) when a human log and machine history share one file; strip-marker discipline makes each writer ignore the other's output. Adapt filename/date scheme and counter names. Omit emoji console styling (host presentation). Extends ledger-contrast-csv-vs-summary: the two formats can coexist in ONE file if writers respect the banner protocol.
