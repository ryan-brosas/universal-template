<!-- capsule-v2 -->
# Open-to-work hidden badge channel — where does recruiter-facing profile state live when LinkedIn renders no visible element you can assert on?

**Source:** linkedin_scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (≡ joeyism-linkedin-scraper identical tree); Codebase Memory `linkedin_scraper`. **Question:** how do you detect the #OPEN_TO_WORK flag reliably across redesigns that keep moving visible badges?

## State flag rides the avatar's title attribute
**Path/Symbol:** `linkedin_scraper/scrapers/person.py:PersonScraper._check_open_to_work` (:124–133), consumed by `scrape` (:62) into `Person.open_to_work` (model default False — see profile-schema). Header text fields (name/location/About) are owned by company-about-section-probe (person.`_get_about` twin) and profile-schema; navigation/auth ordering mechanics live in scraper-base-callbacks + scrape-orchestration-template.
**Signature:** `async _check_open_to_work() -> bool`.
**Data Shape:** bool, default False — absence of evidence means "not advertising", never an error.

### Decisive source
```python
# the badge graphic carries its state machine-readably in the img title:
img_title = await self.get_attribute_safe(
    ".pv-top-card-profile-picture img", "title", default="")
return "#OPEN_TO_WORK" in img_title.upper()
```

**Flow:** scrape() calls this right after name/location, BEFORE section walks; the attribute defaults to "" so a missing avatar degrades to False instead of raising; the uppercase-compare absorbs LinkedIn's own casing.
**Invariant:** detect state through STABLE machine-readable channels (aria/title attributes, data-* URNs) rather than visible-badge classes — the visible badge moved repeatedly across redesigns while the avatar title kept the flag; the predicate is substring-based (`"#OPEN_TO_WORK" in ...upper()`) because the attribute bundles extra text; failure mode is conservative False, matching the model default so schema-total rows survive missing avatars.
**Probe:** deterministic needles at this pin: `.pv-top-card-profile-picture img` :128–129 and `"#OPEN_TO_WORK" in img_title.upper()` :131; unit lane green (`pytest -m unit`, person model tests). Live badge behavior integration-gated (session fixture) — recorded caveat, no fabricated pass.
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "linkedin_scraper", qualified_name: "linkedin_scraper.linkedin_scraper.scrapers.person.PersonScraper._check_open_to_work" });
```

## Verdict
Adopt: attribute-carried state flags with conservative defaults and case-insensitive substring predicates. Adapt the selector and flag token per host; survey aria/title/data-* surfaces FIRST when a visible control keeps moving. Omit the surrounding scrape-order commentary here (owned by scrape-orchestration-template). Coverage caveat: no direct unit test for the getter; evidence is whole-file source read at the cited pin plus graph snippet retrieval.
