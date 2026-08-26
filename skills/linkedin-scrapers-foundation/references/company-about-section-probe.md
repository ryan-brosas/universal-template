<!-- capsule-v2 -->
# About-section text probe — how do I find a company's "About us" paragraph when the page gives you generic <section> wrappers instead of ids?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85b…`; Codebase Memory `joeyism-linkedin-scraper`. **Question:** what is the cheapest reliable probe that locates an about/description section across LinkedIn page generations?

## Heading-prefix scan over sections, then first paragraph wins
**Path/Symbol:** `linkedin_scraper/scrapers/company.py:CompanyScraper._get_about` (:88–110 file, graph :98–116); twin `scrapers/person.py:PersonScraper._get_about` (:135–157); name fallback `_get_name` (:81–86).
**Signature:** `async def _get_about(self) -> Optional[str]`.
**Data Shape:** input = company page DOM; probe = first 50 chars of each section's inner_text; output = Optional[str] (first <p> text of the matching section) or None.

### Decisive source
```python
sections = await self.page.locator('section').all()
for section in sections:
    section_text = await section.inner_text()
    if 'About us' in section_text[:50]:        # prefix window, not full-text search
        paragraphs = await section.locator('p').all()
        if paragraphs:
            return (await paragraphs[0].inner_text()).strip()
return None
# name twin degrades to a sentinel VALUE, not None:
name_elem = self.page.locator('h1').first
... except Exception: return "Unknown Company"
```

**Flow:** enumerate all <section> nodes → cheap prefix test ('About us' within the first 50 chars — headings precede body text in reading order, so this avoids matching prose that merely MENTIONS "about us") → first paragraph inside the winner → strip → return; no match ⇒ None.
**Invariant:** the 50-char PREFIX WINDOW is the false-positive filter; widening it to full-text search would return marketing copy containing the phrase. Failure shape differs by field role: descriptive text degrades to None, but the NAME degrades to a sentinel string ("Unknown Company") because downstream consumers format it unconditionally.
**Probe:** live-DOM path is integration-gated upstream (`pytest tests/test_company_scraper.py -m integration` → fixture skip without linkedin_session.json; executed this pass: 3 skipped). Structural probe: excerpt verified byte-for-byte via source read + graph snippet at pinned HEAD; sibling test `test_company_scraper_about` (:23–29) asserts about-or-name presence when run live. Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "CompanyScraper _get_about about section", limit: 6 });
// → CompanyScraper._get_about :98–116 + PersonScraper._get_about twin :135–157 + TESTS edges
```

## Verdict
Adopt the heading-prefix-window probe for label-less section discovery and the split failure-shape rule (None for optional text vs sentinel for always-formatted fields). Adapt the needle ('About us') and window size to host markup. Omit nothing structural. Pair with overview-vocabulary-classifier (same page, label-free overview chips) — this capsule covers the ABOUT narrative; that one covers the metadata chips.
