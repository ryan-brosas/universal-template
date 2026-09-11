<!-- capsule-v2 -->
# Ledger contrast — append-only CSV audit trail vs rewrite-on-write summary file: which persistence shape does a run-level job/outcome ledger need?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550` (`runAiBot.py:submitted_jobs` :802–826, `failed_job` :765–784, `get_applied_job_ids` :163–176); EasyApplyJobsBot CC-BY-NC 4.0 `main@70fe748` (`linkedin.py:displayWriteResults` :498–503, `applyProcess` result strings :465–496; `utils.py:writeResults` :97–119). Codebase Memory projects of the same names. **Question:** when a bot must record every application outcome for later review, do you append one row per event or rewrite a human-readable summary — and what breaks under each choice?

## Two writers, same data, opposite contracts
**Path/Symbol:** Auto_job_applier `runAiBot.py:submitted_jobs` (:802–826) + `failed_job` (:765–784); EasyApplyJobsBot `linkedin.py:displayWriteResults` (:498–503) → `utils.py:writeResults` (:97–119).
**Signature:** `submitted_jobs(job_id, title, …, questions_list, connect_request) -> None` — 18 fixed columns; `failed_job(…, error, exception, screenshot_name) -> None` — 9 columns; `displayWriteResults(lineToWrite: str) -> None`; `writeResults(text: str) -> None`.
**Data Shape:** Auto_job_applier: append-only CSVs (`file_name`, `failed_file_name`), `csv.DictWriter` with fixed fieldnames, header only when `file.tell() == 0`, values pre-truncated via `truncate_for_csv`. EasyApplyJobsBot: ONE daily text file `"data/Applied Jobs DATA - YYYYMMDD.txt"`, header line + column-title line + `"* <emoji> …"` outcome lines separated by `----` rules; the whole file is re-read on EVERY write.

### Decisive source
```python
# A — append-only ledger (Auto_job_applier): O(1) per event, crash-safe,
# machine-readable, doubles as next-run dedupe state:
with open(file_name, mode='a', newline='', encoding='utf-8') as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    if csv_file.tell() == 0: writer.writeheader()
    writer.writerow({key: truncate_for_csv(v) for key, v in record.items()})

# B — rewrite-on-write summary (EasyApplyJobsBot): pretty, self-numbering,
# but O(file) per event and lossy under crash:
with open(fileName, encoding="utf-8") as file:
    lines = [l for l in file if "----" not in line]   # read ALL, drop separators
with open(fileName, 'w', encoding="utf-8") as f:      # rewrite from scratch
    f.write("---- Applied Jobs Data ---- created at: " + timeStr + "\n")
    f.write("--- Number | Job Title | Company | … | Result \n")
    f.writelines(f"{i+1}. {line}" for i, line in enumerate(lines))  # auto-numbered
```
(A's failure twin `failed_job` mirrors submitted_jobs with its own 9-column schema + screenshot name — schema divergence between success/failure ledgers is deliberate.)

**Flow:** A: outcome classified once (string-outcome-channel) → `submitted_jobs`/`failed_job` append immediately after each attempt → next run hydrates dedupe set from the SAME file (`get_applied_job_ids`). B: `applyProcess` returns an emoji outcome string → `displayWriteResults` prints AND writes → `writeResults` re-reads the day file, filters `----` lines, rewrites numbered.
**Invariant:** A keeps three properties B loses: **append-only = crash-safe** (a kill mid-run leaves complete rows, never a half-rewritten file), **O(1) per event** (B pays O(file) growth per write), and **state+audit in one artifact** (the ledger IS the cross-run dedupe source). B keeps two things A lacks: **self-numbering readability** (humans can eyeball results without a CSV reader) and **daily rotation by filename date**. Both share the tell()==0 header probe and never let a ledger write failure kill the run (A logs + desktop alert; B wraps displayWriteResults in try/except island). Neither survives concurrent writers — single-writer assumption is explicit in both.
**Probe:** graph-resolved symbols with exact lines — Auto_job_applier_linkedIn `runAiBot.submitted_jobs` :802–826, `runAiBot.failed_job` :765–784, `runAiBot.get_applied_job_ids` :163–176; EasyApplyJobsBot `utils.writeResults` :97–119, `linkedin.displayWriteResults` :498–503. Deterministic probes: `grep -c "csv.DictWriter" runAiBot.py` ⇒ 2 vs `grep -c "DictWriter" utils.py` = 0 (EasyApplyJobsBot has no DictWriter — its ledger is plain-text rewrite) / Auto_job_applier `app.py` carries a third site ⇒ 1; no upstream tests pin either writer loop (coverage caveat recorded; adjacent test-pinned seam: Auto_job_applier `tests/test_helpers.py::test_truncate_for_csv_*` pins cell coercion feeding these files).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "submitted_jobs", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "writeResults", limit: 5 });
```

## Verdict
Adopt A's shape for anything machine-consumed or crash-exposed (audit trail, dedupe state, resume): append-only rows, tell()==0 headers, truncation before write, per-event try/except islands. Adopt B's rotation-by-date-filename idea freely; adopt B's rewrite-on-write ONLY for small human-facing summaries that tolerate lossy crashes. Omit: B's emoji-in-data contract (keep emojis to the LOG channel), pyautogui alerts, donate nags. Contrast verdict: **CSV-append wins for state, txt-rewrite wins for presentation — never merge the two jobs into one file**.
