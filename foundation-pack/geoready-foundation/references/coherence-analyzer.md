<!-- capsule-v2 -->
# Semantic coherence — cross-page conflicting definitions, duplicate titles, mixed language

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you detect when a site contradicts itself across pages — the signal AI engines use to distrust a domain?

## Definition extraction + SequenceMatcher title similarity + language consistency
**Path/Symbol:** `src/geo_optimizer/core/coherence_analyzer.py:analyze_coherence` (22–57), `_check_conflicting_definitions` (60–88), `_check_duplicate_titles` (90–116), `_definitions_conflict` (151+).
**Signature:** `analyze_coherence(extracts: list[PageTermExtract]) -> SemanticCoherenceResult`.
**Data Shape:** `PageTermExtract(url, title, h1, key_terms[], definitions[], language)` from the shared `term_extractor`; issues typed `{conflicting_definition, duplicate_title, mixed_language}` with severity ∈ {high, medium, low}; penalties high −10 / medium −5 / low −2 off 100; duplicate-title threshold 0.85 SequenceMatcher ratio.

### Decisive source
```python
score = 100
for issue in issues:
    score -= _PENALTY.get(issue.severity, 2)
score = max(score, 0)
langs = [e.language.split("-")[0] for e in extracts if e.language]   # "en-US" → "en"
if langs:
    most_common = max(set(langs), key=langs.count)
    lang_consistency = langs.count(most_common) / len(langs)
```

**Flow:** term definitions grouped across pages (`X is/refers to/means` patterns via `_extract_defined_term`) → same term with conflicting definitions (negation, incompatible predicates) flags high-severity issues → titles compared pairwise at ≥0.85 similarity flag duplicates → primary-language share reports mixed-language drift. Needs ≥2 pages; fewer returns checked-with-zero-issues.
**Invariant:** The pipeline consumes PRE-EXTRACTED page terms (shared with topic_authority), so coherence costs no extra fetches; conflict detection compares DEFINITIONS of the same term — not prose similarity — which is what makes it cheap and explainable. Penalties are additive-from-100 with floor 0.
**Probe:** `tests/test_coherence.py::test_conflicting_definitions_flagged` (+ duplicate-title/language suites; `PYTHONPATH=src pytest tests/test_coherence.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "coherence analyzer definitions", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt definition-conflict detection as the cheapest self-contradiction check for multi-page sites; adapt thresholds; omit language logic for single-language estates.
