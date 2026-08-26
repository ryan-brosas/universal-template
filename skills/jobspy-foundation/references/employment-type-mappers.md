<!-- capsule-v2 -->
# Employment-type mappers — why does JobType lookup behave three different ways, and which inputs silently miss?

**Source:** JobSpy MIT `main@fda080a373e8`; Codebase Memory `JobSpy`. **Question:** How do site vocabularies and user input map onto the shared JobType enum, and why do hyphenated or capitalized labels fail?

## Enum lookup plane over alias-tuple values
**Path/Symbol:** `jobspy/model.py:JobType` (:10–57, i18n ALIAS TUPLES e.g. FULL_TIME=("fulltime","vollzeit","全职",...)); user path `jobspy/util.py:get_enum_from_value` (:304–308); shared normalizer `jobspy/util.py:get_enum_from_job_type` (:177–185); site twins `jobspy/ziprecruiter/util.py:get_job_type_enum` (:27–31, live) and `jobspy/glassdoor/util.py:get_job_type_enum` (:26–29, ZERO callers — dead); label pre-normalizer `jobspy/indeed/util.py:get_job_type` (:5–17).
**Signature:** all four lookups iterate `for jt in JobType: if s in jt.value ...` — membership against the alias TUPLE, differing only in tie-break, return shape, and miss behavior.
**Data Shape:** aliases are unhyphenated lowercase strings (plus i18n forms with duplicates inside a tuple, e.g. "tempsplein" twice in FULL_TIME); definition order FULL_TIME..VOLUNTEER matters for first/last-match ties.

### Decisive source
```python
# user input: FIRST match, RAISES generic Exception on miss (util.py)
def get_enum_from_value(value_str):
    for job_type in JobType:
        if value_str in job_type.value: return job_type
    raise Exception(f"Invalid job type: {value_str}")

# shared normalizer: LAST-match-wins (res overwritten each loop), None on miss (util.py)
res = None
for job_type in JobType:
    if job_type_str in job_type.value: res = job_type

# ziprecruiter twin: FIRST match returning [member]; glassdoor twin identical body, never called
# indeed pre-normalizer rescues raw labels before the shared normalizer:
job_type_str = attribute["label"].replace("-", "").replace(" ", "").lower()
```

**Flow:** user string -> get_enum_from_value at scrape_jobs entry (raise on typo); site labels -> Indeed strips '-'/spaces + lowercases -> shared normalizer collects MULTIPLE types per job; ZipRecruiter passes raw strings to its twin (first hit wins).
**Invariant:** hyphenated input misses every alias tuple: executed P1b 'full-time' -> Exception('Invalid job type: full-time') while 'fulltime' -> FULL_TIME; raw 'Full-Time' into the zip twin -> None (case-sensitive). First-vs-last tie-break diverges only when an alias appears in two members. The glassdoor twin is dead code (callers=0 confirmed by grep + trace) — copying it gives you a helper nothing calls.
**Probe:** executed excerpts vs live model.py: P1a fulltime->FULL_TIME, teilzeit->PART_TIME; P1b raise; P2 last-match-wins + miss->None; P3 deltid->[PART_TIME], 'Full-Time'->None; P4 indeed normalization ['Full-Time','Part-Time','Unknown-Thing'] -> [FULL_TIME, PART_TIME] (unknowns skipped silently).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", name_pattern: "get_enum_from_value|get_enum_from_job_type|get_job_type_enum|get_job_type", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ONE canonical membership test against alias tuples and decide explicitly: raise-or-None on miss, first-or-last on ties, scalar-or-list return. Adapt alias tuples to your markets. Omit duplicating the helper per site (that is exactly how the dead Glassdoor twin happened). Coverage caveat: f_JT LinkedIn codes are covered separately in linkedin-util-plane.md; no in-repo tests — claims pinned by executed excerpts.