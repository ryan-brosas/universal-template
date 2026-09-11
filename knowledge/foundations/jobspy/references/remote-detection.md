<!-- capsule-v2 -->
# Remote detection — keyword OR-ing across title/description/location, per-site variants

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does each site decide a job is remote, and what are the keyword-set / source-field variants?

## Remote heuristics
**Path/Symbol:** `jobspy/linkedin/util.py:is_job_remote` (88–96); `jobspy/indeed/util.py:is_job_remote` (52–68); `jobspy/naukri/util.py:is_job_remote` (31–37); `jobspy/bdjobs/util.py:is_job_remote` (82–99); `jobspy/google/__init__.py:_parse_job` (197, inline `is_remote`).
**Signature:** `is_job_remote(title, description, location) -> bool` (LinkedIn/Naukri); `is_job_remote(job: dict, description) -> bool` (Indeed); `is_job_remote(title, description=None, location=None) -> bool` (BDJobs).
**Data Shape:** each variant ORs keyword substring matches over a concatenated lowercase string of the available text fields.

### Decisive source
```python
# LinkedIn / Naukri — title + description + location.display_location()
remote_keywords = ["remote", "work from home", "wfh"]
full_string = f'{title} {description} {location}'.lower()
is_remote = any(keyword in full_string for keyword in remote_keywords)

# Indeed — attributes + description + location.formatted.long (OR of three sources)
is_remote_in_attributes = any(any(keyword in attr["label"].lower() for keyword in remote_keywords) for attr in job["attributes"])
is_remote_in_description = any(keyword in description.lower() for keyword in remote_keywords)
is_remote_in_location = any(keyword in job["location"]["formatted"]["long"].lower() for keyword in remote_keywords)
return is_remote_in_attributes or is_remote_in_description or is_remote_in_location

# BDJobs — adds "home based" to the keyword set, and location is optional
remote_keywords = ["remote", "work from home", "wfh", "home based"]
```

**Flow:** each site concatenates its available text fields (title, description, location) and does a case-insensitive substring search for the shared keyword set `["remote", "work from home", "wfh"]`; Indeed ORs across three independent sources (attributes labels, description, formatted long location); BDJobs adds `"home based"` and makes location optional; Google infers inline from the description (`"remote" in description.lower() or "wfh" in description.lower()`).
**Invariant:** the keyword match is a simple substring `any(...)` over lowercased text — no tokenization, no stemming. The `location` text is always rendered via `Location.display_location()` (so internal `US_CANADA`/`WORLDWIDE` members never leak "worldwide" as a false remote hit). Google's inline check is narrower (description only, no `"work from home"`).
**Probe:** no in-repo test suite; verified against source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "is_job_remote remote_keywords wfh", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the keyword-OR heuristic (substring over lowercased concatenated fields, `display_location()` for location). Adapt the keyword set per market (`home based` for BDJobs) and per-source-field availability (Indeed attributes). Omit the Google inline-only variant if you want the fuller LinkedIn/BDJobs multi-field check. Coverage caveat: no in-repo tests; verified against source.
