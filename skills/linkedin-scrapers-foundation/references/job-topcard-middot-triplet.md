<!-- capsule-v2 -->
# Job top-card middot triplet — where do location, posted date, and applicant count come from when LinkedIn packs all three into ONE delimited container text?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85b…`; Codebase Memory `joeyism-linkedin-scraper`. **Question:** how do I extract the three metadata fields of a job posting's unified-top-card without three fragile selectors?

## One container, split on '·', index IS identity
**Path/Symbol:** `linkedin_scraper/scrapers/job.py:JobScraper._get_location/_get_posted_date/_get_applicant_count` (:152–228); canonical example `_get_applicant_count` (:197–222 graph).
**Signature:** `async def _get_<field>(self) -> Optional[str]`.
**Data Shape:** input = `.job-details-jobs-unified-top-card__primary-description-container` first node's `inner_text()`, shaped `"<location> · <posted-ago> · <N applicants>"` (each part may wrap lines). Output = Optional[str]; every failure degrades to None.

### Decisive source
```python
container = self.page.locator('.job-details-jobs-unified-top-card__primary-description-container').first
if await container.count() > 0:
    text = await container.inner_text()
    parts = text.split('·')
    if len(parts) > 2:
        return parts[2].strip().split('\n')[0].strip()   # applicants = parts[2]
# fallback ladder: vocabulary predicates + anti-false-positive guards
for elem in await main_content.locator('span, div').all():
    text = (await elem.inner_text()).strip()
    if text and len(text) < 50:
        if 'applicant' in text.lower() or 'people clicked' in text_lower or 'applied' in text_lower:
            return text
```
(_get_location takes parts[0], _get_posted_date parts[1] — same container, same split.)

**Flow:** primary path: container exists → split('·') → positional part → strip → first line. Fallback ladders per field: location scans span/div for comma/'Remote'/'United States' with guards (`len(text)>3 and len(text)<100`, `not startswith('$')`, skip if equal to the job title); posted date matches 'ago/day/week/hour' with `len<50`; applicant count matches 'applicant/people clicked/applied'.
**Invariant:** the middot INDEX is the field identity — swapping parts[0]/parts[1] silently corrupts data, so the triplet must stay one decision point. Fallback predicates must keep their negative guards (length caps, $ exclusion, title-equality exclusion) or they match salary/title strings.
**Probe:** integration-gated (needs live LinkedIn job page): `pytest tests/test_job_scraper.py -m integration` — currently @pytest.mark.skip (selector rot recorded upstream). Deterministic logic-replay probe executed: `python3 -c "t='San Francisco, CA · 2 days ago · Over 100 applicants'; p=t.split('·'); print(p[0].strip(), '|', p[1].strip().split(chr(10))[0].strip(), '|', p[2].strip().split(chr(10))[0].strip())"` → `San Francisco, CA | 2 days ago | Over 100 applicants`. Live-DOM behavior remains a coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "_get_applicant_count", limit: 5 });
// → JobScraper._get_applicant_count Method scrapers/job.py :197–222 (snippet served, callers=1)
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "JobScraper scrape jobs", limit: 8 });
// → full scrape choreography :39–100
```

## Verdict
Adopt the one-container/middot-index grammar plus guarded vocabulary fallbacks for LinkedIn job cards. Adapt the container class name and predicate vocabularies as LinkedIn rotates them (they rot — see the sibling skip-reason discipline). Omit bare `except: pass` if your host has structured logging; keep the None degradation either way. Caveat: no runnable direct test for this DOM path (upstream skips it too); excerpts verified byte-for-byte at pinned HEAD via get_code_snippet.
