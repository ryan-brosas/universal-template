<!-- capsule-v2 -->
# Overview vocabulary classification — how do you extract labeled fields from DOM that no longer has labels?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c` (≡ linkedin_scraper identical tree); Codebase Memory `joeyism-linkedin-scraper`. **Question:** when LinkedIn's redesign removed dt/dd label structure, how does the scraper still fill website/industry/size/headquarters fields?

## Content-vocabulary classifier with structural fallback
**Path/Symbol:** `linkedin_scraper/scrapers/company.py:CompanyScraper._get_overview` (:118-208).
**Signature:** `async def _get_overview(self) -> dict` → fixed 8-key dict `{website, phone, headquarters, founded, industry, company_type, family_size…}` initialized ALL-None.
**Data Shape:** input: `.org-top-card-summary-info-list__info-item` elements (unlabeled chips); output: the pre-seeded dict, mutated in place; every miss stays `None`.

### Decisive source
```python
if 'employee' in text_lower or 'k+' in text_lower:      # size
    overview['company_size'] = text
elif ',' in text and any(loc in text for loc in ['Washington', …]):  # HQ
    overview['headquarters'] = text
elif any(ind in text_lower for ind in ['software', 'technology', …]): # industry
    overview['industry'] = text
elif 'follower' in text_lower:
    continue                                             # known-junk class
```

**Flow:** (1) seed all-None dict so shape is stable even on total failure; (2) classify each unlabeled info-item by CONTENT vocabulary — employee/k+ → company_size, comma+state-list → headquarters, industry word list → industry, follower → explicit skip-class; (3) website via link hunt (`a[href]` not linkedin + text ∈ {'learn more','website','visit'}); (4) FALLBACK only `if not any(overview.values())` — old dt/dd walk using `xpath=following-sibling::dd[1]`; (5) whole method wrapped in one try/except returning the partial dict. Sibling methods: `_get_name` h1-first with `'Unknown Company'` sentinel (:87-96); `_get_about` scans sections whose first 50 chars contain 'About us', returns first `<p>` (:98-116).
**Invariant:** classification is by CONTENT, never position/order — chips may appear in any sequence; the fallback runs ONLY when the primary pass produced zero fields (never mixes vocab-matched and structure-matched values); a total failure still returns the full-keyed dict, never raises.
**Probe:** `tests/test_company_scraper.py::test_company_model_to_dict/to_json` unit-pin the output model shape; the classification ladder itself is integration-gated behind live `browser_with_session` (test_company_scraper_overview documents the redesign limitation in-source) — coverage caveat stated honestly.
**Retrieve:** `search_graph({project:"joeyism-linkedin-scraper", query:"CompanyScraper _get_overview info_items", limit:5})` resolves `_get_overview` at :118-208.

## Verdict
Adopt: seed-dict-all-None + content-vocabulary classification + zero-progress-only fallback + never-raise contract — portable to any redesigned-DOM extraction. Adapt vocab lists and selectors (rot fast). Omit the hardcoded state list as authoritative geography (extend it); GPL-3 source — patterns only, no verbatim copy beyond fair excerpt.
