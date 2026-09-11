<!-- capsule-v2 -->
# URL queue file round-trip — should a bot's search-URL plan persist across runs, and what happens on each side when the file is missing or half-written?

**Source:** EasyApplyJobsBot CC-BY-NC 4.0 `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot` (184n/454e, FULL). **Question:** how does the writer (`generateUrls`) and reader (`getUrlDataFile`) share `data/urlData.txt`, and which failure modes leave a partial or empty queue?

## Write kernel truncates first, generates inside the open; reader is honest-empty
**Path/Symbol:** `linkedin.py:Linkedin.generateUrls` (:115–125) writes; `utils.py:getUrlDataFile` (:60–73) reads back; sole consumer chain `linkJobApply :128 → :137`.
**Signature:** `generateUrls(self) -> None`; `getUrlDataFile() -> List[str]` (module function).
**Data Shape:** one URL per line in `data/urlData.txt`; lines are blank-tolerant on read (strip + drop empties); directory `data/` bootstrapped with `os.makedirs('data')` guarded by an exists-check (:116–117) — note cookies dir uses `exist_ok=True` instead (linkedin.py :96).

### Decisive source
```python
def generateUrls(self) -> None:
    if not os.path.exists('data'):
        os.makedirs('data')
    try:
        with open('data/urlData.txt', 'w', encoding="utf-8") as file:   # 'w' TRUNCATES old queue
            linkedinJobLinks = utils.LinkedinUrlGenerate().generateUrlLinks()  # INSIDE the with
            for url in linkedinJobLinks:
                file.write(url + "\n")
        utils.prGreen("✅ Apply urls are created successfully, ...")
    except Exception:
        utils.prRed("❌ Couldn't generate urls, make sure you have editted config file line 25-39")

# reader side (utils.py):
try:
    with open('data/urlData.txt', 'r') as file:
        urlData = [line.strip() for line in file if line.strip()]
except FileNotFoundError:
    prRed("FileNotFound:urlData.txt file is not found. Please run ./data folder exists and check config.py values of yours. Then run the bot again")
return urlData   # [] on miss — honest-empty, never raises
```

**Flow:** every run calls `generateUrls()` FIRST (linkJobApply :128) — mode `'w'` destroys the previous plan, then the cross-product generator runs inside the open handle, so a mid-generation crash leaves a PARTIAL file that the subsequent `getUrlDataFile()` faithfully reads as a shorter queue. Read side strips whitespace, drops blanks, and on missing file prints loud red operator guidance and returns `[]`; `main()` then zero-runs through `printSessionSummary(0,…)` without error.
**Invariant:** the queue is a THIS-RUN plan artifact ('w'-regenerated each invocation), NOT cross-run state — never confuse it with dedupe-applied-tracking's appliedJobs CSV (state) or ledger-contrast's summary file (presentation). The generator call living inside the `with` block means truncate-then-generate is not atomic: partial-queue-on-crash is part of the contract, and downstream must tolerate fewer URLs than config implies.
**Probe:** repo ships no tests (standing caveat). Executed byte-for-byte at HEAD this pass: `grep -n "os.makedirs\|data/urlData.txt" linkedin.py utils.py` ⇒ exactly linkedin.py :117/:119 + utils.py :68 (plus unrelated cookies/summary sites); direct reads of both ranges match graph snippets byte-for-byte.
**Coverage:** check_index_coverage(linkedin.py, utils.py) = no_recorded_issue + metadata_match, generation_matches=true @ gen 2026-08-23T00:13:12Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "getUrlDataFile urlDataFile", limit: 5 });
// ⇒ EasyApplyJobsBot.utils.getUrlDataFile Function utils.py 60-73
```

## Verdict
Adopt the honest-empty read contract (loud operator message, `[]`, zero-run instead of crash) and the exists-guarded directory bootstrap; adopt truncate-and-regenerate ONLY if the queue is genuinely a per-run plan. Adapt the error text to point at your real config keys. Omit generating inside the truncated handle if you need all-or-nothing plans — build the list fully, THEN write it in one pass. Contrast: urlToKeywords reverse-parse labeling on the consumer side is owned by displayed-count-page-budget.
