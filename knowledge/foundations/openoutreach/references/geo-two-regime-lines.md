<!-- capsule-v2 -->
# Two jurisdiction regime lines — which countries gate *emailing* vs which gate *collecting*, and what does an unread country code default to?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** When compliance has two different legal questions (may I email this person? may I store this profile?), do I need one country set or two, and how does each treat a missing code?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/geo.py` — `GDPR_COUNTRY_CODES` (:27-41), `is_gdpr_protected` (:44-51), `EEA_UK_CH` (:60-74), `is_eea_located` (:77-87).
**Signature:** `is_gdpr_protected(country_code: str | None) -> bool`; `is_eea_located(country_code: str | None) -> bool`.
**Data Shape:** ISO-3166-1 alpha-2 strings, lowercase set literals. Operator's code comes from onboarding (`SiteConfig.country_code`), a lead's code from the discovery row — neither is ever scraped from a network.
**Graph evidence:** search_graph "geo EEA jurisdiction country gate" (17 total; both predicates + 6 direct tests in top hits); trace inbound `is_eea_located` = exactly two gates: `contacts.service.contribute` (drop before hub store) and `enrichment.lookup.check_lookup`.

### Decisive source
```python
def is_eea_located(country_code: str | None) -> bool:
    """...
    Missing / ``None`` / blank codes default to ``True`` (err on the side of
    exclusion — a false drop costs one lead, a false keep is the only risk)."""
    if not country_code or not country_code.strip():
        return True
    return country_code.strip().lower() in EEA_UK_CH
```

**Flow:** The broad line (`GDPR_COUNTRY_CODES`: EU/EEA+UK+CH **plus** CA/BR/AU/JP/KR/NZ) answers *email-marketing opt-in* and only steers the newsletter default (`default=not is_gdpr_protected(country)` at onboarding). The narrow line (`EEA_UK_CH`: EU-27+EEA+UK+CH only) answers *data collection* and gates hub contribution plus the operator forced-give-back. Same predicate shape, disjoint on purpose: Brazil is email-opt-in but collectable.
**Invariant:** Both predicates fail closed — missing/blank ⇒ protected/excluded ("a false drop costs one lead, a false keep is the only risk"). Note the asymmetry worth porting deliberately: the narrow line strips whitespace (`not country_code.strip()`, `"   "` ⇒ excluded); the broad line checks truthiness only. Neither set is ever derived from a stored toggle — jurisdiction is computed from the code each time.
**Probe:** `tests/test_geo.py` whole (126 L) — `test_country_code_lookup` parametrized incl. `("br", False)`-style opt-in-only rows? No: that test pins the *broad* set (`br` True there), while `test_eea_located_lookup` (:107-108) pins `br/ca/au/jp/kr/nz → False` on the narrow set, `test_eea_located_missing_or_blank_defaults_to_excluded` (:116-119) pins `None`/`""`/`"   "` all ⇒ True, and `test_eea_uk_ch_excludes_email_optin_countries` (:122-126) asserts the six-country `isdisjoint`.
**Coverage:** `check_index_coverage` openoutreach/core/geo.py + tests/test_geo.py → no_recorded_issue / metadata_match @ gen 2026-08-25T20:08:16Z.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "geo EEA jurisdiction country gate", limit: 10, fields: ["signature", "docstring"] });
```

## Verdict
Adopt: two regime lines as two named sets with two predicates, fail-closed defaults, whitespace-stripping on the line that gates storage. Adapt the actual country lists to your jurisdictions and your consumers (contribution gate, consent defaults). Omit the newsletter-default wiring if you have no consent-bearing opt-in.
