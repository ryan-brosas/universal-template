<!-- capsule-v2 -->
# Perception extractor — deterministic "simulated AI view" with mandatory honesty labeling

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you expose what an AI engine would perceive from audit data without ever claiming real AI output?

## Pure aggregation over AuditResult + always-populated disclaimer
**Path/Symbol:** `src/geo_optimizer/core/perception_extractor.py:extract_perception` (15–33), `_extract_citability` (76–92), `_extract_trust` (94+).
**Signature:** `extract_perception(audit_result: AuditResult) -> PerceptionSnapshot`.
**Data Shape:** `PerceptionSnapshot(url, mode="deterministic", brand_name, brand_entity_type, schema_types_present[], citation_worthy_facts[], trust_score, missing_signals[], ai_readable_summary, disclaimer)`; every sub-result optional → getattr-with-default everywhere.

### Decisive source
```python
"""...IMPORTANT: The output is always labeled as 'simulated perception', not real AI output."""

# Citation-worthy facts: methods that passed with HIGH signal only
for method in methods:
    if score / max_score >= 0.8 and name:
        snapshot.citation_worthy_facts.append(name)

# composite_score is 0-25 (5 layers × 5), not 0-100 — rescaled for the snapshot
```

**Flow:** brand name = primary_name else first names_found; entity type resolved by precedence org > person > product against schema found_types; services from ecommerce_signals keys; schema types passed through; citability grade + facts at the ≥0.8 ratio bar; trust rescaled from /25; factual claims and missing signals folded in; `_build_ai_readable_summary` renders a plain-text paragraph an LLM could consume as context.
**Invariant:** Zero LLM calls, zero I/O — pure function of the audit result; `mode="deterministic"` and `disclaimer` are structural fields, not documentation: any consumer rendering the snapshot must surface the simulated-perception label. The 0.8 ratio bar keeps "citation-worthy" a high-confidence list.
**Probe:** `tests/test_perception_extractor.py::test_disclaimer_always_present` (+ extraction suites; `PYTHONPATH=src pytest tests/test_perception_extractor.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "extract_perception snapshot", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt labeled-deterministic aggregation whenever you present heuristic output "as an AI would see it"; adapt field set; omit nothing — the honesty labeling generalizes.
