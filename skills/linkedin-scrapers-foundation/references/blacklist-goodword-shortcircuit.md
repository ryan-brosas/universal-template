<!-- capsule-v2 -->
# Blacklist good-word short-circuit — how do I enforce employer red-lines cheaply, remember verdicts within a run, and carry the evidence in the failure itself?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** scanning every "About company" section against a blocklist is slow and false-positive-prone — what whitelist-first ordering and exception-as-evidence shape keeps it fast and auditable?

## Whitelist short-circuit, ValueError carrying the about-text, session-scoped verdict sets
**Path/Symbol:** `runAiBot.py:check_blacklist` (:328–348); card-level consumers in `get_job_main_details` (:304–315) and the pipeline catch at :898–907.
**Signature:** `check_blacklist(rejected_jobs: set, job_id: str, company: str, blacklisted_companies: set) -> tuple[set, set, WebElement] | ValueError`.
**Data Shape:** two session-scoped sets grow monotonically during a run (rejected job IDs, blacklisted company names); the raised ValueError's MESSAGE is the full about-company text plus the offending word — evidence travels IN the exception.

### Decisive source
```python
for word in about_company_good_words:            # 1. whitelist FIRST
    if word.lower() in about_company:
        skip_checking = True; break              #    one hit ⇒ never scan the blocklist
if not skip_checking:
    for word in about_company_bad_words:         # 2. blocklist only if no good word
        if word.lower() in about_company:
            rejected_jobs.add(job_id); blacklisted_companies.add(company)
            raise ValueError(f'\n"{about_company_org}"\n\nContains "{word}".')   # evidence payload
# card level, BEFORE clicking into a job:
if company in blacklisted_companies: skip = True     # remembered verdicts skip instantly
elif job_id in rejected_jobs: skip = True
```

**Flow:** open job → scroll to About-company box → lowercase text → good-word scan short-circuits checking entirely → else bad-word hit mutates BOTH session sets and raises with the quoted text → pipeline catch writes the failed-jobs ledger row ("Found Blacklisted words in About Company") and continues to the next card. Every later card from that company (or that job ID) skips at LIST level without ever opening details.
**Invariant:** the whitelist outranks the blocklist (one good word vetoes all bad words) — order matters and is the false-positive defense; verdict memory is session-scoped by design (fresh run re-checks, so list edits apply next run); the exception is the data channel, not a log side effect.
**Probe:** no upstream test pins check_blacklist — source-grounded seam (orchestration-level caveat consistent with job-run-orchestration). Direct probe: read :328–348; behavioral anchor = suite executes green without touching this path.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "check_blacklist blacklisted_companies", limit: 6 });
// → runAiBot.check_blacklist runAiBot.py :328-348 (single top hit)
```

**Retrieve:** see above.

## Verdict
Adopt whitelist-before-blocklist ordering, monotonic session verdict sets consulted at collection level, and exceptions whose message carries the triggering content. Adapt word lists per domain; consider persisting blacklisted companies cross-run ONLY deliberately (this repo resets per run on purpose). Omit regex/ML classification — substring containment is the contract here. Contrast with get_job_description's bad-word gate (:392–401), which checks JOB text and skips WITHOUT set mutation.
