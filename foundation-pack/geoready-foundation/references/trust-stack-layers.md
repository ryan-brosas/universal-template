<!-- capsule-v2 -->
# Trust stack — how do you grade site trust in five independent 5-point layers with zero new fetches?

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How does an aggregate trust score reuse prior audit outputs without double-counting signals across layers?

## Five-layer aggregation, each capped at 5, composite graded by threshold table
**Path/Symbol:** `src/geo_optimizer/core/trust_stack.py:audit_trust_stack` (373–415), layer scorers (50–356), `_compute_grade` (362–367).
**Signature:** `audit_trust_stack(soup, base_url, response_headers, brand_entity, schema, meta, content, negative_signals) -> TrustStackResult`.
**Data Shape:** `TrustLayerScore(name, label, score, signals_found[], signals_missing[], details{})` ×5 → `TrustStackResult(checked, technical, identity, social, academic, consistency, composite_score 0–25, grade A–F, trust_level)`; bands from config `TRUST_STACK_GRADE_BANDS` (22→A/excellent, 17→B/high, 11→C/medium, 6→D/low).

### Decisive source
```python
# Layer separation is enforced by SUBTRACTION, not by luck (fix #390):
# social links counted for Social Trust must not inflate Academic Trust's
# "external sources" signal — cardinality must match content.external_links_count
social_link_count = _count_social_links(soup) if soup else 0     # every individual <a>
academic_external_count = max(content.external_links_count - social_link_count, 0)
if academic_external_count >= 2:
    layer.score += 1

# statistics vs numbers are DIFFERENT counters and both land in details:
layer.details["statistics_count"] = stats_count   # regex: %, "according to a study", N≥10 + studi*
layer.details["numbers_count"] = content.numbers_count   # generic counter from citability
```

**Flow:** technical = HTTPS(+2)/HSTS/CSP/X-Frame-Options-or-CSP-frame-ancestors (each +1) from headers; identity = consistent brand/about/contact/Organization-schema/author (each +1); social = sameAs present (+1) / sameAs≥3 (+1) / KG pillar (+1) / testimonials via class|itemprop|blockquote≥20 words (+1) / social links (+1); academic = numbers≥3 (+1) / non-social external≥2 (+1) / authority domains (doi.org, arxiv, ncbi...) (+1) / References-heading match incl Italian ("fonti","bibliografia") (+1) / `_STATISTICS_RE` matches ≥2 (+1); consistency = brand consistency (+2)/no mixed signals/desc≈meta/dateModified. Every layer clamps `min(score,5)`.
**Invariant:** Zero HTTP fetches — the module consumes ONLY already-computed sub-results plus the homepage soup/headers; each signal appears in exactly one layer (the subtraction rule above), so composite ≤25 stays meaningful; missing signals are recorded (`signals_missing`) not skipped, making the report explainable.
**Probe:** `tests/test_trust_stack.py::TestComposite::test_grade_a_massimo` (+ full layer suites; `PYTHONPATH=src pytest tests/test_trust_stack.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "trust stack composite grade", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt capped-layers + cross-layer subtraction + found/missing evidence lists as the shape for any composite rubric; adapt domain lists and language-specific heading patterns; omit the specific point values if your rubric differs but keep per-layer clamping.
