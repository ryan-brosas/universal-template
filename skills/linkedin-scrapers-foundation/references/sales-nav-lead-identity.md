<!-- capsule-v2 -->
# Sales Nav lead → canonical profile URL — how do I turn a Sales Navigator result row into a public `/in/<id>` link without opening the profile?

**Source:** hassan-sales-nav-profiles-scraper (no LICENSE file — all-rights-reserved; pattern-only) `main@e294ac0` (2026-06-09); Codebase Memory `hassan-sales-nav-profiles-scraper`. **Question:** what is the DOM-to-identity extraction ladder that converts Sales Nav's private `fs_salesProfile` encodings into canonical public URLs, and what fallback order avoids wrong identities?

## data-scroll-into-view URN split → /sales/lead/ href split → raw href
**Path/Symbol:** `linkedin_scraper.py:main` inner loop (:175–214); pagination tail (:237–251); container-scoped scroll (:154–164).
**Signature:** per element: `href = el.get_attribute('href')`; ladder produces `profile_link: str`; identity sources in strict priority — (1) ancestor `[data-scroll-into-view]` attribute, (2) the anchor's own `/sales/lead/<ID,%20NAME,...>` href, (3) raw href as-is.
**Data Shape:** Sales Nav encodes the member id TWICE per row: `data-scroll-into-view="fs_salesProfile:(<memberId>,<slug>,...)"` on the row container and `https://www.linkedin.com/sales/lead/<memberId>,...` in the link; both reduce to `https://www.linkedin.com/in/<memberId>/`. Name lives OUTSIDE the anchor: `span[data-anonymize="person-name"]` scoped to `ancestor::li`, falling back to `ancestor::div[contains(@class,"artdeco-list__item")]`, then the element's own text.

### Decisive source (ladder condensed)
```python
# 1) PREFERRED: the row container carries the composite URN — split off the first field
ancestor_div = element.locator('xpath=ancestor::div[@data-scroll-into-view]').first
urn = ancestor_div.get_attribute('data-scroll-into-view')
if 'fs_salesProfile:(' in urn:
    member_id = urn.split('fs_salesProfile:(')[1].split(',')[0]
    profile_link = f"https://www.linkedin.com/in/{member_id}/"

# 2) FALLBACK: parse the SAME id out of the sales-lead href
if not profile_link and '/sales/lead/' in href:
    member_id = href.split('/sales/lead/')[-1].split(',')[0]
    profile_link = f"https://www.linkedin.com/in/{member_id}/"

# 3) LAST RESORT: emit whatever the href is (still a lead, not an /in/ URL)
if not profile_link:
    profile_link = href

# NAME: scope the anonymized-name span to the ROW, not the anchor
container = element.locator('xpath=ancestor::li').first \
         or element.locator('xpath=ancestor::div[contains(@class,"artdeco-list__item")]').first
name = container.locator('span[data-anonymize="person-name"]').first.inner_text()
```
Supporting seams: start page parsed FROM THE PASTED URL (`parse_qs(query)['page']`) instead of always restarting at 1 (:45–55); results container scrolled, never the body — 10 × `scrollTop += 800` with 3 s settles inside `#search-results-container` (:154–164); batch bookkeeping appends a visible separator + page list to the sheet every 2 pages (:229–235; deep dive: `in-sheet-page-set-marker`, switch/reset kernel in `sheet-switch-batch-reset`); next-button ladder `.artdeco-pagination__button--next` → `[aria-label="Next"]` gated by `.is_disabled()` (:238–248); teardown deliberately does NOT close the browser (AdsPower owns the session lifecycle) (:259; deep dive: `cdp-attach-run-shell-ownership`).
**Flow:** paste search URL → resume from its `page` param → per page: wait lead-panel selector (20 s timeout = end of results ⇒ stop) → container scroll → collect anchors → per-anchor identity ladder + name ladder → append `[name, profile_link]` row → every-2-pages sheet separator → click enabled Next or stop.
**Invariant:** the composite-ID split ALWAYS takes field [0] after the paren (`split(',')[0]`) because subsequent fields are name/slug fragments that would corrupt the URL; identity extraction must try the row attribute BEFORE the href — the href can be a generic sales route while the attribute pins the exact member; per-row work sits in try/except+continue so one malformed card cannot kill the sweep; the loop's terminal condition is a MISSING selector (timeout), not a page count.
**Probe:** repo has no tests — coverage caveat. Deterministic probes: `grep -n "fs_salesProfile" linkedin_scraper.py` ⇒ exactly :184/:185 (single decisive site); `grep -c "ancestor::" linkedin_scraper.py` ⇒ 4 scoping calls; graph anchor `linkedin_scraper.main` resolves in project `hassan-sales-nav-profiles-scraper`.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "hassan-sales-nav-profiles-scraper", query: "fs_salesProfile data-scroll-into-view sales lead", limit: 5 });`

## Verdict
Adopt the three-step identity ladder with strict precedence (row attribute → lead href → raw) and the comma-first-field split rule; adopt name-from-row-scoped-selector rather than anchor text. Adapt the output sink (this repo writes straight to Google Sheets with hard-coded IDs and a COMMITTED API KEY — do not port credentials; inject your own storage). Omit nothing else structurally. Contrast: profile-schema normalizes Voyager/DOM ids AFTER acquisition via pydantic validation; this capsule is the ACQUISITION-side twin for Sales Nav where no API payload exists — same canonical `/in/<id>` target, different extraction surface. maximo3k variant (prospect_scraper_sales_navigator.py :31–122) implements the same container-scoped scroll + disabled-next stop with per-page CSV writes instead of sheets.
