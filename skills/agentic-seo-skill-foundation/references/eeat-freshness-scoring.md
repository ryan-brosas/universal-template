<!-- capsule-v2 -->
# eeat + freshness scorers — how do you turn trust and recency signals into bounded scores?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** What is each scorer's additive ladder, and what date semantics can silently flip the freshness score?

## E-E-A-T signal checker
**Path/Symbol:** `scripts/eeat_signal_checker.py:check_eeat` (:52-130), `CREDENTIAL_RE` (:14-16), `FIRST_HAND_RE` (:17-19).
**Signature:** `check_eeat(source: str, timeout: int = 15) -> dict`.
**Data Shape:** `{url, score≤100, signals{authors(≤20), credential_markers(≤20), first_hand_experience_markers(≤20), policy_links(≤20), trust_links(≤20), external_citations}, issues, fetch_error}`.

### Decisive source
```python
score += 20 if authors else 0
score += min(20, len(credential_hits) * 7)
score += min(20, len(experience_hits) * 7)
score += 15 if policy_links else 0
score += 15 if trust_links else 0
score += min(10, len(external_citations) * 2)
```

**Flow:** author harvest from meta/span/a name=author + rel=author + class regex + schema author/reviewedBy/publisher (deduped sorted set) → credential markers ("phd","certified","reviewed by","fact-checked","years of experience",…) → FIRST-HAND experience markers ("we tested","hands-on","case study","original research",…) → policy links (editorial/fact-check/corrections/ethics) vs trust links (about/contact/privacy/terms/team) distinguished by text-or-href regex pairs → additive ladder above, capped at 100. Max reachable = 105 raw (20+20+20+15+15+10) so the cap binds only on saturated pages.

## Freshness checker
**Path/Symbol:** `scripts/freshness_checker.py:check_freshness` (:69-152), `DATE_RE` (:13-16), `_parse_date` (:29-40), `_schema_dates` (:57-64).
**Signature:** `check_freshness(source: str, timeout: int = 15, today: date | None = None) -> dict` (`today` injectable for deterministic tests; CLI `--today` flag mirrors it).
**Data Shape:** `{url, score, latest_date, age_days, dates(≤50 with source tags), old_years, stale_stat_sentences, schema_date_mismatch, issues, fetch_error}`.

### Decisive source
```python
latest = max([...parsed_dates...] or modified_dates or published_dates or [], default=None)
...
elif age_days is not None:
    score -= min(45, max(0, age_days - 365) // 30)   # grace year, then ~1pt/30d capped 45
score -= min(25, stale_stat_count * 5)
score -= 15 if mismatch else 0
```

**Flow:** collect dates from five tagged sources (meta whitelist {article:published_time, article:modified_time, date, last-modified, dc.date}, `<time datetime>`, schema datePublished/dateModified via recursive JSON walk, body DATE_RE ISO + "Month D, YYYY") → latest = newest parsed body/meta/time date, FALLING BACK to max(modified) then max(published) when none parseable in the primary set → stale-stat scan: sentence has a statistic AND a year ≤ today−3 → mismatch when max(dateModified) < max(datePublished) → scoring: start 100; no date −35; age beyond 365-day grace −min(45,(age−365)//30); stale stats −5 each capped 25; mismatch −15.
**Invariant:** The fallback chain means a page citing ONLY dateModified still gets scored — but the mismatch check compares the TWO schema families independently, so mixed-source maxima can disagree. `--today` injection is the determinism contract (fixture test passes `_parse_date("2026-05-15")`).
**Probe:** `grep -cF 'min(20, len(credential_hits) * 7)' scripts/eeat_signal_checker.py` (= 1); `grep -cF '{"article:published_time", "article:modified_time", "date", "last-modified", "dc.date"}' scripts/freshness_checker.py` (= 1); fixture test asserts `freshness["latest_date"] == "2026-05-01"` and no mismatch.
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"eeat freshness score signals","limit":5}'`.

## Verdict
Adopt both additive ladders as content-quality primitives; adapt marker vocabularies per language; omit body-date scraping if your corpus guarantees structured dates. Probes executed green @69199160; freshness fixture test green in the 34/34 run.
