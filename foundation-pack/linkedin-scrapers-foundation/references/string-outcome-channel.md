<!-- capsule-v2 -->
|# String-outcome channel — how do I keep a Selenium bot's per-item results greppable and crash-isolated without an exception taxonomy?

**Source:** LinkedIn-Easy-Apply-Bot Apache-2.0 `master@8471c58` (2025-11-28); EasyApplyJobsBot CC BY-NC-SA 4.0 (learn-only) `main@70fe748`. **Question:** when a bot classifies every outcome (applied / already / blacklisted / cannot-apply), what is the minimal contract that keeps classification, logging, and counting consistent across thousands of iterations?

## `* prefix` result strings + emoji counters + outer try/except island
**Path/Symbol:** `easyapplybot.py:EasyApplyBot.apply_to_job` (:325–370, string set at :342–363) + `write_to_file` (:372–387); EasyApplyJobsBot variant: `linkedin.py:linkJobApply` (:208–281, counter family :129–135).
**Signature:** `apply_to_job(jobID) -> bool` BUT the human-readable outcome travels as a `* ...` string captured in a local (`string_easy`) and logged + persisted per job; EasyApplyJobsBot returns outcome STRINGS from `applyProcess` and counts by substring test.
**Data Shape:** outcome vocabulary — `"* has Easy Apply Button"`, `"*Applied: Sent Resume"`, `"*Did not apply: Failed to send Resume"`, `"* Already Applied"`, `"* Contains blacklisted keyword"`, `"* Doesn't have Easy Apply Button"`; CSV row = `[timestamp, jobID, job, company, attempted, result]` where `attempted = button is not False`.

### Decisive source
```python
# CLASSIFY-ONCE, USE-EVERYWHERE: one local carries the human verdict,
# a bool carries the machine verdict, both derive from the same branch
if button is not False:
    if any(word in self.browser.title for word in blackListTitles):
        string_easy = "* Contains blacklisted keyword";  result = False
    else:
        button.click()
        result = self.send_resume()
        string_easy = "*Applied: Sent Resume" if result else "*Did not apply: Failed to send Resume"
elif "You applied on" in self.browser.page_source:
    string_easy = "* Already Applied";  result = False
else:
    string_easy = "* Doesn't have Easy Apply Button";  result = False

log.info(f"\nPosition {jobID}:\n {self.browser.title} \n {string_easy} \n")
self.write_to_file(button, jobID, self.browser.title, result)   # attempted = button is not False

# COUNTER FAMILY (EasyApplyJobsBot): count by substring membership on result strings
if "Just Applied" in result: countApplied += 1
# counts kept for: applied / blacklisted / alreadyApplied / cannotApply → session summary
```
The whole loop body sits inside ONE broad try/except whose handler just prints — any single job page (deleted, gated, redesigned) degrades to a failed line instead of killing a multi-hour sweep; per-job state (button presence) doubles as the `attempted` audit column.
**Flow:** probe easy-apply button → title-keyword blacklist check → click+fill+submit → classify into fixed string vocabulary → log line + CSV append + substring counters → next job regardless of exceptions.
**Invariant:** every terminal branch assigns BOTH the string and the boolean from the same decision point (no drift between what the log says and what the ledger records); strings are stable grep anchors (`* Already Applied`, `Just Applied`) that downstream tooling can count; the exception island wraps PER-JOB work only, so the run-level counters always survive to print the session summary.
**Probe:** no automated tests in either repo — coverage caveat. Deterministic probes: `grep -c "string_easy =" easyapplybot.py` ⇒ 6 assignment sites covering all branches (LinkedIn-Easy-Apply-Bot repo root); `grep -n 'count.*+=' linkedin.py` enumerates the EasyApplyJobsBot counter family at :129–135 (init) and :205/:209/:246/:269/:274/:279 (increments); graph anchor `LinkedIn-Easy-Apply-Bot.easyapplybot.EasyApplyBot.apply_to_job` resolves :325–370.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "LinkedIn-Easy-Apply-Bot", query: "apply_to_job write_to_file string_easy already applied", limit: 5 });`

## Verdict
Adopt the contract: classify once into a small closed string vocabulary, derive booleans/counters from it rather than re-testing, persist `(attempted, result)` per item, and wrap each iteration in a catch-all island so long sweeps degrade gracefully. Adapt by promoting the vocabulary to an enum whose str value IS the log line (keeps grep-ability, kills typo drift like `"*Applied"` vs `"* Applied"`); add the session-summary printer (utils.printSessionSummary pattern). Omit nothing structural — but do not inherit the substring-counter fragility for new code (`"Already applied" in result` breaks silently if wording changes; enum identity comparison is the hardened port). Contrast: scraper-base-callbacks streams progress to sinks DURING a scrape; this pattern governs OUTCOME bookkeeping after each discrete action — the two compose as event stream vs. result ledger.
