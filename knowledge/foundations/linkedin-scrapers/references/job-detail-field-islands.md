<!-- capsule-v2 -->
# Job-detail identity & description islands — how do I pin WHO is hiring and WHAT the role says on a job page when the metadata triplet already has its own capsule?

**Source:** linkedin_scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (≡ joeyism-linkedin-scraper identical tree); Codebase Memory `linkedin_scraper`. **Question:** what are the selection rules for job TITLE, company NAME vs company URL, and DESCRIPTION — the four getters that need judgment beyond one container split?

## Title / company-text-vs-logo / first-href-URL / heading-anchored description
**Path/Symbol:** `linkedin_scraper/scrapers/job.py:JobScraper._get_job_title` (:102–110), `_get_company` (:112–125), `_get_company_url` (:127–141), `_get_description` (:224–240); scrape order + Job assembly :39–100. Sibling capsules own the rest of this file: job-topcard-middot-triplet (location/posted/applicant '·' grammar + vocabulary fallbacks), model-dump-contract-validator-placement (Job model validators), scrape-orchestration-template (ceremony).
**Signature:** all `async _get_*() -> Optional[str]`, bare `except: pass` islands — a getter degrades ITS field, never the scrape.
**Data Shape:** company NAME and company URL come from the SAME selector (`a[href*="/company/"]`) under DIFFERENT rules — text-bearing-link scan vs first-anchor href; description prefers a semantic anchor climb over any generic container.

### Decisive source
```python
# NAME: iterate ALL company anchors; skip logo-only links by TEXT shape
for link in await self.page.locator('a[href*="/company/"]').all():
    text = (await link.inner_text()).strip()
    if text and len(text) > 1 and not text.startswith('logo'):
        return text                      # first link with real words wins

# URL: FIRST anchor's href — strip tracking, absolutize relative
href = await self.page.locator('a[href*="/company/"]').first.get_attribute('href')
if '?' in href: href = href.split('?')[0]
if not href.startswith('http'): href = f"https://www.linkedin.com{href}"

# DESCRIPTION: heading-anchored ancestor climb BEFORE generic article
about_heading = self.page.locator('h2:has-text("About the job")').first
article = about_heading.locator('xpath=ancestor::article[1]')
description = await article.inner_text()   # else: page.locator('article').first
```

**Flow:** title waits up to 5s on `h1` first (the only getter that WAITS — everything after it assumes render); name scans anchors for text quality (>1 char, not 'logo'-prefixed); url takes locator.first's href through query-strip then relativize-absolutize; description climbs from the "About the job" heading to its enclosing article, falling back to the page's first article. Each result feeds the progress ladder inside scrape().
**Invariant:** name and URL rules MUST stay different — the first anchor often IS the logo image (empty/alt text), so using .first for the name yields logos while filtering-by-text yields names; the URL rule tolerates that because hrefs carry identity even inside logo links; query-strip precedes dedupe/absolutize so tracked and clean URLs collapse to one company_linkedin_url; description must climb to the SEMANTIC container (article) or boilerplate leaks into the field.
**Probe:** executed at this pin: unit lane green (`pytest -m unit`; test_job_model_to_dict/to_json pins the receiving model); deterministic needles: `startswith('logo')` :121, `split('?')[0]` :135, `ancestor::article[1]` :229. Live DOM stays integration-gated (session fixture). Coverage caveat: getters have no direct unit tests — evidence is whole-file source read + get_code_snippet at the cited pin.
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "linkedin_scraper", qualified_name: "linkedin_scraper.linkedin_scraper.scrapers.job.JobScraper._get_description" });
```

## Verdict
Adopt: text-quality scan for display names vs first-href for identity URLs, query-strip→absolutize ordering, heading-anchored semantic-container climb for long text, single wait-for-render gate before cheap reads. Adapt the anchor substring and article semantics per host. Omit nothing silently: if you take the middot triplet from job-topcard-middot-triplet, take THESE four with it — one without the other scrapes half a job page.
