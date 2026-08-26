<!-- capsule-v2 -->
# Date-normalization ladders — how does each board express posting recency and normalize it to date_posted?

**Source:** JobSpy MIT `main@fda080a373e8`; Codebase Memory `JobSpy`. **Question:** What is each adapter's recency input format, where does it degrade to None, and which clock does it trust?

## Comparative ladder plane (integration view over five boards)
**Path/Symbol:** Glassdoor ageInDays math `jobspy/glassdoor/__init__.py:178–181` (inside _process_job 164–218); BDJobs format ladder `jobspy/bdjobs/util.py:parse_date` (:32–54) over `constant.date_formats` (:26–32); Naukri relative-label ladder `jobspy/naukri/__init__.py:_parse_date` (:266–287, called at :164); cross-refs: LinkedIn datetime-attr fallback (linkedin-card-parsing.md #343), Google positional days_ago [12] (google-adapter.md).
**Signature:** `Glassdoor._process_job -> date | None`; `bdjobs.util.parse_date(date_text) -> datetime | None`; `Naukri._parse_date(label: str, created_date: int) -> date | None`.
**Data Shape:** inputs are either structured ages (ageInDays int, createdDate ms epoch), free-text labels ('today', 'just now', 'few hours', 'N days ago', 'Deadline: ...'), or fixed strptime formats [%d %b %Y, %d-%b-%Y, %d %B %Y, %B %d, %Y, %d/%m/%Y]; outputs are naive dates or None.

### Decisive source
```python
# Glassdoor: arithmetic on a structured day-count; None when missing
age_in_days = job["header"].get("ageInDays")
date_diff = (datetime.now() - timedelta(days=age_in_days)).date()
date_posted = date_diff if age_in_days is not None else None

# BDJobs: strip prefix, try five formats, swallow everything -> None
if "Deadline:" in date_text: date_text = date_text.replace("Deadline:", "").strip()
for fmt in date_formats:
    try: return datetime.strptime(date_text, fmt)
    except ValueError: continue
return None

# Naukri: label first, ms-epoch fallback
if 'today' in label or 'just now' in label or 'few hours' in label: parsed_date = date.today()
#   'N days ago' regex path ... ; else: datetime.fromtimestamp(created_date / 1000).date()
```

**Flow:** board payload -> ladder (structured count / label parse / format list) -> naive date -> JobPost.date_posted -> orchestrator sorts by it descending within each site.
**Invariant:** every ladder DEGRADES TO NONE rather than inventing a date; all three shown trust the local naive clock (datetime.now()/date.today()) — porters in UTC-only services must pin a timezone; BDJobs double try/except means malformed input can never crash the pipeline; Naukri prefers the human label over the authoritative epoch (label checked BEFORE created_date in the today-path).
**Probe:** no runner (recorded block). Source-pinned by MCP snippets + direct reads of the cited ranges; bdjobs date_formats enumerated from constant.py:26–32; Naukri call order pinned by :164 -> :266–287 trace. LinkedIn/Google variants already behavior-captured in their capsules.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "parse_date ageInDays createdDate days ago date_posted", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt degrade-to-None ladders keyed to each source's native recency shape, and keep ONE normalization boundary before sorting. Adapt format lists/label vocabularies per market; pin a timezone instead of trusting the naive clock. Omit label-over-epoch preference unless your source's labels are more trustworthy than its timestamps. Coverage caveat: comparative capsule; per-board details remain in linkedin-card-parsing.md / google-adapter.md / naukri-adapter.md.