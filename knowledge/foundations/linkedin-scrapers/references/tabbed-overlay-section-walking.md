<!-- capsule-v2 -->
# Tabbed & overlay section walking — how do I scrape LinkedIn's Interests tablist and the contact-info overlay dialog without guessing which tab is active?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (`scrapers/person.py`). Codebase Memory `joeyism-linkedin-scraper`. **Question:** how do I drive an ARIA tablist (click each tab, read its tabpanel) and a modal overlay (walk `<h3>` sections) so I capture every interest category and every contact type?

## Tablist driving + overlay section walk
**Path/Symbol:** `linkedin_scraper/scrapers/person.py:PersonScraper._get_interests` (:758–842), `_map_interest_tab_to_category` (:866–879), `_get_contacts` (:1023–1103), `_map_contact_heading_to_type` (:1105–1122). **Signature:** `_get_interests(base_url) -> list[Interest]`; `_get_contacts(base_url) -> list[Contact]`.
**Data Shape:** Interests are `[role="tab"]` elements; each tab's content lives in a sibling `[role="tabpanel"]` with `li/listitem` rows. Contacts come from `overlay/contact-info/` dialog with `<h3>` section headings mapped to types (profile/website/email/phone/twitter/birthday/address).

### Decisive source
```python
# tablist: click every tab, then read its tabpanel
for tab in tabs:
    tab_name = (await tab.text_content()).strip()
    category = self._map_interest_tab_to_category(tab_name)
    await tab.click()
    await self.wait_and_focus(0.5)
    tabpanel = interests_section.locator('[role="tabpanel"]').first
    list_items = await tabpanel.locator('li, listitem').all()
    # ... parse each into Interest(name, category, linkedin_url)

# contact overlay: walk h3 headings, map to type, read links/text under each
for section_heading in contact_sections:
    heading_text = (await section_heading.text_content()).strip().lower()
    contact_type = self._map_contact_heading_to_type(heading_text)
    if not contact_type: continue
    links = await section_container.locator('a').all()
    # email -> strip mailto:, phone/birthday/address -> text_content() fallback
```

**Flow:** Interests — locate the section by `h2:has-text("Interests")`, climb to the tablist ancestor (fallback `ancestor::*[4]`), enumerate `[role="tab"]`, click each in turn, wait, then read the active `[role="tabpanel"]`; category is derived from the tab label substring ("compan"→company, "group", "school", "newsletter", "voice"/"influencer"). Contacts — navigate to `overlay/contact-info/`, wait for the `dialog`/`[role="dialog"]`, walk `<h3>` headings, map each to a type, then read links (stripping `mailto:` for email) or fall back to raw `text_content()` for non-link types (birthday/phone/address).
**Invariant:** tab clicks are sequential and stateful — you MUST click tab N before reading its panel, and you must read the panel immediately after the click (only one panel is live at a time). Contact type is derived from the heading, never from the link href, because website/email/phone links are indistinguishable by href alone. Non-link contact values need the heading text stripped out of the container text.
**Probe:** `tests/test_person_scraper.py` exercises the flow behind the session fixture; the two heading→type mappers are pure and unit-testable. Coverage: person.py `no_recorded_issue`+`metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "_get_interests", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "_get_contacts", limit: 5 });
```

## Verdict
Adopt the click-then-read tablist discipline and the heading→type mapping with link/text dual extraction; adapt the tab labels, heading text, and selector families (rot against live LinkedIn); omit the bring_to_front focus hack. Probe caveat: extraction is source-grounded; mappers are pure.
