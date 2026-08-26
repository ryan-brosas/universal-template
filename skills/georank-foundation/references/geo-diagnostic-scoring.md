<!-- capsule-v2 -->
# GEO diagnostic scoring — which deterministic rules score a page's AI-readability, and how do they combine?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** What exact rule set scores schema.org coverage, meta/OG completeness, content structure, and citation density for generative-engine optimization — and what weights fuse them into one 0–100 score?

## Four deterministic checkers + admin-weighted fusion
**Path/Symbol:** `backend/app/tasks/diagnose.py`: `_check_schema` :224–261, `_check_meta` :263–319, `_check_content` :321–400, `_check_citations` :402–465, `_calculate_overall_score` :594–615; weights default `DEFAULT_DIAGNOSTIC_RULE_WEIGHTS` :191–196 (schema .30 / content .30 / meta .20 / citation .20), admin-editable via `runtime_settings._build_diagnostic_rule_config`.
**Signature:** `_check_*(soup: BeautifulSoup[, base_domain: str]) -> dict`; `_calculate_overall_score(schema_score, content_score, meta_score, citation_score, weights: dict | None = None) -> int`.
**Data Shape:** Schema: JSON-LD `@type` values flattened from lists AND `@graph` recursion (`_iter_jsonld_nodes`); recommended = WebSite/Organization/FAQPage/Article/BreadcrumbList. Meta: 14 boolean checks (title/lang/description/canonical/viewport/robots/favicon/og:*×5/twitter:card). Content: heading counts, first-para >80 chars, char count, alt ratio, FAQ-like headings regex `(faq|常见问题|问题|q&a)`. Citations: external vs authority-domain sets (arxiv, doi, nature, gov, edu …) vs social set.

### Decisive source
```python
coverage_ratio = round((len(set(unique_types) & set(recommended)) / len(recommended)) * 100)
score = min(100, max(len(unique_types) * 16, coverage_ratio))   # breadth OR coverage, whichever higher
```
```python
score = 0
if has_single_h1: score += 20          # exactly one H1
if has_h2_structure: score += 20       # >=2 H2
if first_para_quality: score += 20     # >80 chars direct answer
if character_count > 800: score += 20
if image_alt_ratio >= 60: score += 10
if faq_like_sections >= 1 or len(lists) >= 2: score += 10
```
```python
total = sum(max(0.0, float(v or 0)) for v in active_weights.values())
if total <= 0: active_weights = DEFAULT_DIAGNOSTIC_RULE_WEIGHTS   # all-zero admin input falls back
normalized = {k: max(0.0, float(w)) / total for ...}
return round(s*ns + c*nc + m*nm + x*nx)
```

**Flow:** crawl HTML → four independent scorers emit `{...checks..., score}` → overall = weighted round → LLM turns the numbers into prioritized recommendations with a full RULE-BASED DEGRADED twin (same output shape: summary/strengths/gaps/urgent/recommended/phase_plan P0-P2) when the provider call fails or returns non-JSON.
**Invariant:** All four scorers are PURE functions of the soup (+base_domain) — no I/O, fully unit-testable. Score components clamp at min(100, …). The degraded recommender must produce the SAME JSON contract as the LLM path so downstream rendering never branches on provider success.
**Probe:** `backend/tests/test_diagnose_rules.py` (7 tests incl. list-valued @type flattening and @graph traversal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "_check_schema", limit: 5 });
// verified line-exact: diagnose.py :224–261
```

## Verdict
Adopt the checker/fusion split for any page-quality scorer (SEO, accessibility, AEO); adapt thresholds and weight defaults to your rubric; omit the Chinese copy in degraded recommendations. Direct tests green under real runner.
