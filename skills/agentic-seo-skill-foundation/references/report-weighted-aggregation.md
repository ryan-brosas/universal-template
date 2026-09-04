<!-- capsule-v2 -->
# weighted-average report aggregation — how do 14 script scores become one overall grade without dead categories skewing it?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** Why is hreflang's score sometimes None, and what breaks if the porter "fixes" that to 0?

## Config-driven score compiler
**Path/Symbol:** `scripts/generate_report.py:calculate_overall_score` (:437-577), weights source `resources/config/scoring.json` mirrored in `DEFAULT_SCORING_CONFIG` (:36-52).
**Signature:** `calculate_overall_score(data: dict, scoring_config: dict | None = None) -> {"overall","categories","weights","scoring_version"}`.
**Data Shape:** 14 category keys (security8, social5, robots8, broken_links10, internal_links8, redirects3, llms_txt5, pagespeed13, onpage10, readability8, entity5, link_profile7, hreflang5, duplicate_content5 — sums 100); per-category scores 0-100 or None.

### Decisive source
```python
else:
    # No hreflang = single language site, skip from weighting
    scores["hreflang"] = None
...
for k, w in weights.items():
    if k in scores:
        val = scores.get(k)
        if val is not None:
            total_weight += w
            weighted_sum += val * w
overall = round(weighted_sum / total_weight) if total_weight else 0
```

**Flow:** run 12 sub-scripts (`analyses` list :398-411; entity/link_profile/hreflang/duplicate_content marked supplementary) → derive each category score with its own shape: robots = base60 +20 sitemaps +2/AI-managed-bot capped 100 (404→20, else 0); broken_links = max(0, 100 − broken/total×300); onpage/article = presence-checklist around a 50 base; readability piecewise (≥60→100, ≥30→50+linear×50/30, else ×50/30); entity = found×15 + wikidata25 + wikipedia25 − issues×10; link_profile = 70 ±link-density −orphans×5 −dead-ends×3; duplicates = 100−dupes×20−thin×10 → **hreflang: tags found ⇒ 100 − critical×30 − high×15 − medium×5; none found ⇒ None** → weighted average over non-None categories only (weight denominator renormalizes), then None coerced to 0 AFTER aggregation purely so the UI never sees null.
**Invariant:** The None-skip is a semantic exclusion, not missing data: scoring a single-language site 0/100 for hreflang would drag every such site's overall down by up to 5 points of phantom failure. The post-aggregation None→0 coercion exists ONLY for display. Bands live in scoring.json ({90 A+ Excellent … 0 F Critical}); narrative SKILL.md uses a DIFFERENT 7-category weight table — two rubrics for two audiences, do not unify them blindly.
**Probe:** `grep -cF 'scores["hreflang"] = None' scripts/generate_report.py` (= 2); `grep -cF 'weighted_sum += val * w' scripts/generate_report.py` (= 1); `grep -cF 'base = 60' scripts/generate_report.py` (= 1); config parity: DEFAULT_SCORING_CONFIG weights == resources/config/scoring.json (both sum 100 over 14 cats). Direct tests: `tests/test_reporting.py::test_scoring_config_loads_weights_from_resource_file` (pins pagespeed=13 AND sum==100), `test_calculate_overall_score_uses_config_weights`, `test_markdown_report_contains_score_card_and_findings`.
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"calculate_overall_score weighted hreflang","limit":5}'`.

## Verdict
Adopt renormalizing weighted aggregation + None-as-exclusion semantics for any multi-check composite score; adapt category sets and weights via config file only; omit the second UI-facing rubric if you have one source of truth. Probes executed green @69199160.
