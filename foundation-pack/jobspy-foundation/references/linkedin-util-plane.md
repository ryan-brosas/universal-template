<!-- capsule-v2 -->
# LinkedIn job-type/level/industry util plane — single-letter codes, criteria-table parsers, enum-membership trap

**Source:** JobSpy MIT `main@fda080a`. **Question:** How do LinkedIn-specific enums map to query codes and back from page text, and where does the mapping silently produce `None` or crash?

## LinkedIn util plane
**Path/Symbol:** `jobspy/linkedin/util.py` whole file (96L) — `job_type_code` (:7–14), `parse_job_type` (:17–39), `parse_job_level` (:42–62), `parse_company_industry` (:65–85), `is_job_remote` (:88–96); enum matchers in `jobspy/util.py` — `get_enum_from_job_type` (:177–185), `get_enum_from_value` (:304–308).
**Signature:** `job_type_code(JobType) -> str` one of `F/P/I/C/T`, default `""`. `parse_job_type(soup) -> list[JobType] | None` (note the TWO falsy shapes). `parse_job_level(soup) -> str | None` (verbatim case). `parse_company_industry(soup) -> str | None`.
**Data Shape:** all three parsers anchor on `<h3 class="description__job-criteria-subheader">` by header TEXT (`"Employment type"` / `"Seniority level"` / `"Industries"`) and read `find_next_sibling("span", class_="description__job-criteria-text description__job-criteria-text--criteria")`.

### Decisive source
```python
# linkedin/util.py — request-side code table
def job_type_code(job_type_enum: JobType) -> str:
    return {
        JobType.FULL_TIME: "F", JobType.PART_TIME: "P", JobType.INTERNSHIP: "I",
        JobType.CONTRACT: "C", JobType.TEMPORARY: "T",
    }.get(job_type_enum, "")

# response-side normalization: lower() AND hyphen-strip BEFORE enum lookup
employment_type = employment_type_span.get_text(strip=True)
employment_type = employment_type.lower()
employment_type = employment_type.replace("-", "")
return [get_enum_from_job_type(employment_type)] if employment_type else []

# jobspy/util.py — SUBSTRING membership, last-match wins
def get_enum_from_job_type(job_type_str: str) -> JobType | None:
    res = None
    for job_type in JobType:
        if job_type_str in job_type.value:
            res = job_type
    return res
```

**Flow:** scrape builds `f_JT=job_type_code(...)` only when a job_type was requested; details-page parse normalizes the "Employment type" span then resolves through the alias-tuple enum; level and industry are plain text extraction.
**Invariants:** (1) `get_enum_from_job_type` uses SUBSTRING `in` over each member's tuple of aliases and keeps iterating — LAST matching member wins, so alias overlap across members is resolved by enum declaration order, not specificity; its sibling `get_enum_from_value` (:304–308) RAISES `Exception(f"Invalid job type: {value_str}")` on miss instead of returning None — the two look-alikes are NOT interchangeable (orchestrator uses the raising one on user input; LinkedIn's parser uses the silent one on scraped text); (2) EXECUTED-VERIFIED EDGE: `parse_job_type` returns `[]` when the span is missing, but when the span EXISTS with unrecognized text it returns `[None]` (lookup yields None, list-wrapped anyway) — pydantic then REJECTS the JobPost (`ValidationError`; `job_type: list[JobType] | None` cannot hold `[None]`), which surfaces as a card-level exception and, under LinkedIn's card policy (`__init__.py:163–164`), raises `LinkedInException` killing that scrape; a porter must either keep this fail-loud edge deliberately or filter None before wrapping; (3) `job_type_code`'s `.get(enum, "")` means PER_DIEM/NIGHTS/OTHER/SUMMER/VOLUNTEER silently send NO f_JT filter rather than erroring; (4) LIVE CRASH (executed-verified): `_process_job:240` calls `job_details.get("job_level", "").lower()` but `parse_job_level` returns explicit `None` under an EXISTING key, so the `.get` default never fires — `AttributeError: 'NoneType' object has no attribute 'lower'`; with `linkedin_fetch_description=True`, any job page lacking a "Seniority level" section kills that card into `LinkedInException` (:163–164), aborting the WHOLE scrape mid-run. Safe fix a porter should adopt: `(job_details.get("job_level") or "").lower()`. The empty-dict branch (fetch off) IS protected by the default; (5) `is_job_remote` formats `description=None` via f-string into the literal `"None"` inside the haystack — no TypeError (executed-verified), but a porter who pre-normalizes fields should know this sentinel can never match remote keywords.
**Probe:** anchored at the `jobspy/` package root (ALL paths below relative to it):
`grep -cF 'string=lambda text: "Employment type" in text' linkedin/util.py` → 1 · `grep -cF 'employment_type.replace("-", "")' linkedin/util.py` → 1 · `grep -cF '[get_enum_from_job_type(employment_type)] if employment_type else []' linkedin/util.py` → 1 · `grep -nE 'if job_type_str in job_type.value' util.py` → 183 · `grep -nE 'raise Exception\(f"Invalid job type: \{value_str\}"\)' util.py` → 308. All executed green at pin `fda080a`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", name_pattern: "parse_job_level|job_type_code|is_job_remote|parse_company_industry", limit: 10 });
```
(live-verified: all resolve line-exact under `JobSpy.jobspy.linkedin.util.*`; total:8.)

## Verdict
Adopt the F/P/I/C/T code table and header-text-anchored criteria parsing. Adapt the enum matcher to your own alias vocabulary — but keep ONE policy: silent-last-match for scraped text, raising for user input. Omit the verbatim-case level field if your schema already lowercases everywhere. Coverage caveat: no upstream tests; verified against source at `fda080a`.
