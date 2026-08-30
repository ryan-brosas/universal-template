<!-- capsule-v2 -->
# Impact-ordered recommendations — how does a fix list know which repair pays the most points?

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How are recommendations bucketed AND re-ranked by recoverable score without unstable ordering?

## Priority buckets + stable recoverable-points sort
**Path/Symbol:** `src/geo_optimizer/core/audit.py:build_recommendations` (79–381), `_recoverable` (367–373).
**Signature:** `build_recommendations(base_url, robots, llms, schema, meta, content, ai_discovery=None, signals=None, brand_entity=None, webmcp=None, negative_signals=None, prompt_injection=None, score_breakdown=None, multimodal=None) -> list[str]`.
**Data Shape:** internal segment lists per category; `score_breakdown` is the dict from `compute_score_breakdown` (negative_penalty stored NEGATIVE).

### Decisive source
```python
def _recoverable(category: str | None) -> int:
    if score_breakdown is None or category is None:
        return 0
    if category == "negative_penalty":
        return -score_breakdown.get(category, 0)          # penalty magnitude = what's recoverable
    return CATEGORY_MAX.get(category, 0) - max(0, score_breakdown.get(category, 0))

def _flatten(segs):
    if score_breakdown is not None:
        segs = sorted(segs, key=lambda seg: _recoverable(seg[0]), reverse=True)
    return [rec for _, seg in segs for rec in seg]        # sorted() is STABLE: ties keep static order

return _critical + _flatten(high_segs) + _flatten(medium_segs) + _flatten(low_segs)
```

**Flow:** CRITICAL items (X-Robots noindex, noai meta directive, LLM-injection findings) bypass sorting and come first → HIGH (robots/llms/meta-title) → MEDIUM (meta/schema/brand/content/negative) → LOW (signals/ai-discovery/webmcp/multimodal); within each bucket categories reorder by `CATEGORY_MAX − earned` so the biggest-payoff fixes surface first. CDN/JS-blocking warnings append AFTER the builder returns (audit.py:629–641).
**Invariant:** Sorting happens on CATEGORY SEGMENTS, never on individual message strings — messages within a category keep authoring order, and Python's stable sort guarantees ties revert to the declared static priority. A porter who sorts flattened strings destroys deterministic output; one who forgets the negative-penalty magnitude flip ranks the penalty as already-earned points.
**Probe:** `tests/test_audit_contract.py::test_web_api_score_breakdown_has_eight_categories` pins the breakdown keys feeding this ranking; recommendation presence covered by `tests/test_core.py` audit suites (`PYTHONPATH=src pytest tests/test_audit_contract.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "build_recommendations recoverable priority", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt buckets + stable category-level re-ranking by recoverable value for any advice engine tied to a weighted score; adapt bucket names/thresholds; omit the specific GEO copy strings.
