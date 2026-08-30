<!-- capsule-v2 -->
# Profile section expansion & fallback navigation — how do I scrape a LinkedIn profile's Experience/Education/Accomplishments sections that lazy-load behind expanders?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (`scrapers/person.py` 1122L). Codebase Memory `joeyism-linkedin-scraper`. **Question:** what is the main-page-first-then-details-page fallback and per-section category mapping that a porter must reproduce to get every profile section without missing lazy-loaded rows?

## Main-page-first + details-page fallback
**Path/Symbol:** `linkedin_scraper/scrapers/person.py:PersonScraper._get_experiences` (:159–220), `_get_educations` (:521–579), `_get_accomplishments` (:881–935). **Signature:** `_get_<section>(base_url) -> list[Model]`; each tries the main profile page first, falls back to `urljoin(base_url, "details/<path>/")` when empty.
**Data Shape:** each section is an ordered list of typed models (Experience/Education/Accomplishment); accomplishment sections are a fixed `(url_path, category)` table of 8: certifications, honors, publications, patents, courses, projects, languages, organizations.

### Decisive source
```python
# main-page-first: locate the section by heading, walk ancestor to a list container
experience_heading = self.page.locator('h2:has-text("Experience")').first
experience_section = experience_heading.locator('xpath=ancestor::*[.//ul or .//ol][1]')
if await experience_section.count() == 0:
    experience_section = experience_heading.locator('xpath=ancestor::*[4]')
items = await experience_section.locator('ul > li, ol > li').all()

# fallback: navigate to the dedicated details page and re-scroll to force lazy load
exp_url = urljoin(base_url, "details/experience")
await self.navigate_and_wait(exp_url)
await self.page.wait_for_selector("main", timeout=10000)
await self.wait_and_focus(1.5)
await self.scroll_page_to_half()
await self.scroll_page_to_bottom(pause_time=0.5, max_scrolls=5)
```

**Flow:** try the collapsed main-page section first (cheap, one navigation) → if it yields zero items, navigate to `details/<path>/`, wait for `main`, scroll to force the paged list to materialize → fall back from the modern `<list>/<listitem>` / `ul > li` selectors to the legacy `.pvs-list__container > .pvs-list__paged-list-item` when the modern ones are absent → parse each item, dedupe by title (`seen_titles` set, :918–926), skip empty sections on the `text="Nothing to see for now"` marker (:902–906).
**Invariant:** every section must be reachable by TWO independent paths (collapsed main page AND dedicated details page) because LinkedIn renders different subsets on each; the scroll-before-parse ordering is mandatory or the paged list never materializes. Accomplishment parsing tolerates arbitrary span order by keyword-sniffing ("Issued by", "Credential ID", month names) rather than fixed position (:954–1000).
**Probe:** `tests/test_person_scraper.py` exercises the PersonScraper flow behind the live-session fixture (integration-gated); model round-trips (`test_person_model_to_dict`) are network-free. Coverage: person.py `no_recorded_issue`+`metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "_get_experiences", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "_get_accomplishments", limit: 5 });
```

## Verdict
Adopt the main-page-first-then-details-fallback ladder, the `(url_path, category)` table, and the seen-titles dedupe; adapt the heading text, section paths, and selector families (they rot against live LinkedIn); omit the bring_to_front focus hack in headless runs. Probe caveat: section extraction is source-grounded, not test-pinned.
