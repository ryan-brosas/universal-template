<!-- capsule-v2 -->
# Pipe row three-island extraction — how do you assemble one ledger row from several fragile DOM reads so one failure degrades a field instead of the row?

**Source:** EasyApplyJobsBot CC-BY-NC 4.0 `main@70fe7484ebe78646fc8e2dd2612459f37eed7a9f`; Codebase Memory `EasyApplyJobsBot`. **Question:** what is the degradation and delimiter contract when title, detail, and workplace chips are scraped independently into ONE pipe-joined string?

## Three independent try-islands degrade to ""; middot is folded INTO the row delimiter
**Path/Symbol:** `linkedin.py:Linkedin.getJobProperties` (:317–356); consumers gate on its output at linkJobApply :208.
**Signature:** `getJobProperties(self, count: int) -> str` returning `"{count} | {title} | {detail}{location}"`.
**Data Shape:** title from `h1.job-title` via `get_attribute("innerHTML").strip()`; detail from `div.job-details-jobs//div` `.text` with `.replace("·","|")` after a FIXED `time.sleep(5)`; workplace from repeated accent-label spans, each appended as `" | " + span.text`; every island resets its field to `""` on exception behind `config.displayWarnings`-gated notices.

### Decisive source
```python
try:
    jobTitle = self.driver.find_element(By.XPATH, "//h1[contains(@class, 'job-title')]") \
                       .get_attribute("innerHTML").strip()
    ...
except Exception as e:
    if config.displayWarnings: utils.prYellow("⚠️ Warning in getting jobTitle: " + str(e)[0:50])
    jobTitle = ""                                  # island 1 degrades

try:
    time.sleep(5)                                  # FIXED settle — not jittered
    jobDetail = self.driver.find_element(By.XPATH, "//div[contains(@class, 'job-details-jobs')]//div") \
                           .text.replace("·", "|")  # middot → PIPE: delimiter harmonization
    ...
except Exception:
    jobDetail = ""                                 # island 2 degrades

for span in jobWorkStatusSpans:
    jobLocation = jobLocation + " | " + span.text  # each chip pre-pipes itself
...
textToWrite = str(count) + " | " + jobTitle + " | " + jobDetail + jobLocation
```

**Flow:** three sequential try-islands; each owns exactly one field and never raises outward. Location chips prepend their own separator so they chain directly onto detail without an extra join. Row tail is RAGGED by design: if detail/location islands fail, the row just ends earlier.
**Invariant:** field failures must degrade VALUES, not drop rows (the orchestrator's blacklist substring gate at :208 still runs on whatever came back). The load-bearing trap: `.replace("·","|")` harmonizes LinkedIn's middot-separated metadata INTO the same character used as the column delimiter — any consumer that later pipe-SPLITS these rows sees shifted columns wherever detail text contained a middot (location·company·workplace fragments become phantom columns). Keep delimiters and content transforms disjoint in ports (or document the collision). The blacklist annotations inside this method are owned by blacklist-inline-annotation-gate; this capsule owns assembly/degradation only.
**Probe:** repo ships no tests (standing caveat). Executed byte-for-byte at HEAD: `grep -n 'replace("·"' linkedin.py` ⇒ exactly :334; `grep -c '" | "' linkedin.py` ⇒ 8 join/annotation sites; direct read :317–366 matches graph snippet byte-for-byte.
**Coverage:** check_index_coverage(linkedin.py) = no_recorded_issue + metadata_match @ gen 2026-08-23T00:13:12Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "EasyApplyJobsBot", query: "getJobProperties blacklisted jobDetail row", limit: 5 });
// ⇒ EasyApplyJobsBot.linkedin.Linkedin.getJobProperties Method linkedin.py 317-356
```

## Verdict
Adopt per-field try-islands with empty-string degradation and displayWarnings-gated notices for ledger rows built from multiple DOM reads. Adapt the fixed sleep(5) to your readiness signal (it is a hardcoded settle, not jittered pacing). Omit content→delimiter folding: pick a content transform that cannot collide with the row grammar (strip or re-encode middots). Contrast: na-preserving-row-extraction (Sales Nav) degrades to "NA" sentinels per column; this bot degrades to empty strings and ragged tails.
