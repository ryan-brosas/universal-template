<!-- capsule-v2 -->
# Weighted scoring engine — how do nine audit categories fold into one honest 0–100 GEO score?

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How is the composite score computed, clamped, and kept in sync with per-category maxima?

## SCORING dict + breakdown + floor/ceiling guards
**Path/Symbol:** `src/geo_optimizer/core/scoring.py:compute_geo_score` (39–59), `compute_score_breakdown` (62–84).
**Signature:** `compute_geo_score(robots, llms, schema, meta, content, signals=None, ai_discovery=None, brand_entity=None, negative_signals=None) -> int`; `compute_score_breakdown(...) -> dict[str,int]`.
**Data Shape:** All inputs are typed result dataclasses from `models/results.py` (optional ones default to `None` → category scores 0). Weights live ONLY in `models/config.py:SCORING` (robots 18 / llms 18 / schema 16 / meta 14 / content 12 / brand_entity 10 / signals 6 / ai_discovery 6) plus `CATEGORY_MAX`, `ROBOTS_PARTIAL_SCORE=10`, penalties (`NEGATIVE_PENALTY_{HIGH,MED,LOW}` = 5/3/1, `XROBOTS_NOINDEX_PENALTY=5`).

### Decisive source
```python
def compute_geo_score(...) -> int:
    breakdown = compute_score_breakdown(...)
    total = sum(breakdown.values())
    if total > 100:
        _logger.warning("Score overflow: %d > 100 (check SCORING weights)", total)   # fix #316
    return max(0, min(total, 100))     # fix M-5: floor guard — never negative

# negative_penalty is stored NEGATIVE in the breakdown and simply summed:
"negative_penalty": _penalty_negative_signals(negative_signals),
```

**Flow:** each `_score_*` helper reads boolean/numeric flags off its result dataclass → graduated sub-scores (e.g. llms depth tiers at `LLMS_DEPTH_WORDS=1000` / `LLMS_DEPTH_HIGH_WORDS=5000`; schema richness clamped `max(0, min(richness, SCORING["schema_richness"]))`; incomplete schema types earn 1pt instead of full) → breakdown dict → sum → clamp [0,100] with overflow warning.
**Invariant:** Two sync traps a porter must not break: (1) split-budget constants are asserted at import time against their SCORING parent keys — `assert SCORING["brand_entity_coherence"] == _BRAND_COHERENCE_NAME + _BRAND_COHERENCE_DESC` (scoring.py:234-240) — because formatters sum SCORING by `"brand_"` prefix and would double-count a new sub-key; (2) `get_score_band` bands (`excellent≥86/good≥68/foundation≥36/critical`) must match the hardcoded ladder in `citability._compute_grade`. Wildcard-only robots permission earns `ROBOTS_PARTIAL_SCORE` (10), an ALTERNATIVE to (not additive with) `robots_citation_ok`.
**Probe:** `tests/test_core.py::TestComputeGeoScore` + `tests/test_schema_richness_394.py` (graduated richness; run `PYTHONPATH=src pytest tests/test_core.py tests/test_schema_richness_394.py -q` → green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "compute_score_breakdown SCORING weights", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the weights-table + breakdown-dict + clamp-with-warning shape and the assert-tie of split budgets; adapt category names/thresholds to your domain; omit the Italian-comment heritage and any category you don't audit (keep them as explicit 0 entries so downstream consumers see all eight keys).
