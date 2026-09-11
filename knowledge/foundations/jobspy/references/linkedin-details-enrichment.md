<!-- capsule-v2 -->
# LinkedIn details-page enrichment — signup-redirect guard, criteria-table twins, applyUrl extraction

**Source:** JobSpy MIT `main@fda080a`. **Question:** When `linkedin_fetch_description=True`, how does one job page yield description, level, industry, type, function, logo, and direct URL — and which fetches silently produce an EMPTY dict?

## Job-page enrichment plane
**Path/Symbol:** `jobspy/linkedin/__init__.py:LinkedIn._get_job_details` (:249–302) and `_parse_job_url_direct` (:330–345); regex `job_url_direct_regex = re.compile(r'(?<=\?url=)[^"]+')` compiled once in `__init__` (:71).
**Signature:** `_get_job_details(job_id: str) -> dict` (7 keys); `_parse_job_url_direct(soup) -> str | None`.
**Data Shape:** return dict keys: `description, job_level, company_industry, job_type, job_url_direct, company_logo, job_function`. EVERY consumer uses `job_details.get(key)` / `.get(key, "")` — a `{}` return degrades every field to None/empty without crashing `_process_job`.

### Decisive source
```python
response = self.session.get(f"{self.base_url}/jobs/view/{job_id}", timeout=5)
response.raise_for_status()
except:
    return {}                                  # transport failure -> empty dict
if "linkedin.com/signup" in response.url:
    return {}                                  # AUTH WALL: guest redirected to signup
...
div_content = remove_attributes(div_content)   # strip ALL attrs before serialization
description = div_content.prettify(formatter="html")
if self.scraper_input.description_format == DescriptionFormat.MARKDOWN:
    description = markdown_converter(description)
elif ... PLAIN: description = plain_converter(description)
h3_tag = soup.find("h3", text=lambda text: text and "Job function" in text.strip())
...
job_url_direct_match = self.job_url_direct_regex.search(
    job_url_direct_content.decode_contents().strip())   # <code id="applyUrl">
```

**Flow:** GET `/jobs/view/<id>` (5 s timeout) → raise_for_status inside try (any HTTP error → `{}`) → **signup-redirect guard**: if LinkedIn bounced the guest to `linkedin.com/signup`, return `{}` instead of parsing a login page → find the `show-more-less-html__markup` div (class_ lambda = substring match, survives modifier classes) → `remove_attributes` then prettify → convert per `ScraperInput.description_format` → mine three "job criteria" h3s by their header TEXT (`Employment type` / `Seniority level` / `Industries`) each followed to `find_next_sibling("span", class_="description__job-criteria-text description__job-criteria-text--criteria")`; `Job function` is the odd one out using `find_next` (not sibling) with class `description__job-criteria-text` only; logo from `img.artdeco-entity-image` attr `data-delayed-url`; direct URL from `<code id="applyUrl">` contents via lookbehind regex after `?url=` + `unquote`.
**Invariants:** (1) ALL failure modes funnel to `{}` — a porter who raises here breaks the whole scrape on ONE dead job page; (2) the signup guard must check `response.url` AFTER redirects, not the requested URL; (3) attribute stripping happens BEFORE prettify/markdown conversion — order matters or tracking params leak into output; (4) employment-type normalization lives in util (`lower()` + `-` removal), while level is kept VERBATIM case at source and lowercased ONLY at the JobPost construction site (:240 `job_level=job_details.get("job_level", "").lower()`); (5) the applyUrl payload embeds the target URL as a query param, so the lookbehind `(?<=\?url=)` + `unquote` pair is the contract — decoding before matching would break the pattern.
**Probe:** anchored at the `jobspy/` package root (ALL paths below relative to it):
`grep -cF 'linkedin.com/signup' linkedin/__init__.py` → 1 · `grep -cF 'show-more-less-html__markup' linkedin/__init__.py` → 1 · `grep -cF 'remove_attributes(div_content)' linkedin/__init__.py` → 1 · `grep -cF 'id="applyUrl"' linkedin/__init__.py` → 1 · `grep -nF 'job_url_direct_regex = re.compile' linkedin/__init__.py` → line 71 · `grep -cE '"Job function" in text.strip\(\)' linkedin/__init__.py` → 1 · `grep -cF 'data-delayed-url' linkedin/__init__.py` → 1 · `grep -nE 'if job_type_str in job_type.value' util.py` → 183 · `grep -nE 'raise Exception\(f"Invalid job type: \{value_str\}"\)' util.py` → 308 · `grep -nF 'job_level=job_details.get("job_level", "").lower()' linkedin/__init__.py` → 240. All executed green at pin `fda080a`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", name_pattern: "_get_job_details|_parse_job_url_direct", limit: 10 });
```
(live-verified: both resolve line-exact under `JobSpy.jobspy.linkedin.LinkedIn.*`.)

## Verdict
Adopt the empty-dict degradation contract, post-redirect signup guard, and strip-before-serialize ordering. Adapt the criteria-table selectors to your markup generation (header-text anchors are more stable than positional siblings). Omit the direct-apply extraction when your host never applies off-site. Coverage caveat: no upstream tests; verified against source at `fda080a`.
