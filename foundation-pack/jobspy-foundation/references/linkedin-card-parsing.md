<!-- capsule-v2 -->
# LinkedIn card parsing — salary span, title/company/location selectors, datetime fallback (#343)

**Source:** JobSpy MIT `main@fda080a` (pin HEAD = upstream fix #343). **Question:** How is a guest search-card turned into a `JobPost` before any details fetch, and which fields can silently degrade?

## Card → JobPost pre-details plane
**Path/Symbol:** `jobspy/linkedin/__init__.py:LinkedIn._process_job` (:173–247); helpers `_get_location` (:304–328); `jobspy/util.py:currency_parser`.
**Signature:** `_process_job(job_card: Tag, job_id: str, full_descr: bool) -> Optional[JobPost]`; `_get_location(metadata_card: Optional[Tag]) -> Location`.
**Data Shape:** every selector miss degrades to a default (`title="N/A"`, `company="N/A"`, empty `company_url=""`, `date_posted=None`) — the card NEVER fails the run.

### Decisive source
```python
salary_values = [currency_parser(value) for value in salary_text.split("-")]
...
datetime_tag = metadata_card.find("time", class_="job-search-card__listdate")
if not datetime_tag and metadata_card:
    datetime_tag = metadata_card.find("time", class_="job-search-card__listdate--new")
...
try:
    date_posted = datetime.strptime(datetime_str, "%Y-%m-%d")
except:
    date_posted = None
```

**Flow:** salary span → split on `-` → `currency_parser` per side → currency = first char of raw text (`$`→`USD`, else verbatim e.g. `€`) → `int()` truncation; title from `span.sr-only`; company from `h4.base-search-card__subtitle > a` with query-string-stripped href; location via comma-split arity ladder (`0/1 part` → country-only Location; 2 parts → city+state; 3 parts → city+state+country resolved through `Country.from_string`, which RAISES on unknown strings — an unrecognized country name in a card kills that card into the LinkedInException path rather than yielding a degraded row); datetime tag with `--new` fallback → strict `%Y-%m-%d` parse with bare except → None. Then optional `_get_job_details(job_id)` when `linkedin_fetch_description=True`.
**Invariants:** (1) DATE FALLBACK ORDER IS LOAD-BEARING (upstream fix #343): new-format cards carry ONLY `listdate--new`, so checking plain `listdate` first and falling back keeps both generations parseable — reversing the order or dropping the fallback nulls dates on new listings; (2) the bare-except strptime means a malformed datetime string silently becomes `date_posted=None`, never a crash; (3) `li-<id>` id prefix comes from stripping query string then taking the LAST `-` segment of the href path; (4) salary currency inference is FIRST-CHAR-of-text, so multi-char symbols like `€` work but `US$` would yield `"U"` — porters must re-derive for their market's symbol grammar.
**Probe:** anchored at the `jobspy/` package root (all paths below relative to it):
`grep -cF 'listdate--new' linkedin/__init__.py` → 1 · `grep -cF '%Y-%m-%d' linkedin/__init__.py` → 1 · `grep -cF 'class_="base-search-card"' linkedin/__init__.py` → 1 · `grep -cF 'salary_text.split("-")' linkedin/__init__.py` → 1 · `grep -cF "li-{job_id}" linkedin/__init__.py` → 1 · `grep -cE 'len\(parts\) == 3' linkedin/__init__.py` → 1. All executed green at pin `fda080a`. No upstream tests — source-verified caveat applies.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", name_pattern: "_process_job|_get_location", limit: 10 });
```
(live-verified via name_pattern `_process_job`: `JobSpy.jobspy.linkedin.LinkedIn._process_job` + `_get_location` resolve line-exact.)

## Verdict
Adopt the degrade-don't-fail card contract and the two-generation datetime fallback order. Adapt the location arity ladder to your target's locale format (the 2-part vs 3-part split assumes "City, State" / "City, State, Country"). Omit salary first-char-currency if you have structured currency data. Coverage caveat: no upstream tests; verified against source at `fda080a`.
