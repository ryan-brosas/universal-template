<!-- capsule-v2 -->
# AI intent mapping — weighted pattern taxonomy over headings with schema-requirement gating

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you infer which AI-search intents a page serves and grade coverage per intent?

## Intent pattern table → text scoring → schema cross-check → radar output
**Path/Symbol:** `src/geo_optimizer/core/intent_mapping.py:audit_intent_mapping` (198–275), `_INTENT_PATTERNS` (38–77), `_check_schema_for_intent` (139+).
**Signature:** `audit_intent_mapping(soup, base_url, content, meta, schema) -> IntentMappingResult`.
**Data Shape:** per intent `{patterns: [regex], schema_required: {types}, weight}` — informational 1.0, navigational 0.8, transactional 1.0, commercial 1.2 (commercial weighted highest because comparison queries are the citation battleground); page text = H1 + title + H2–H6 + meta description via `_CONTENT_SECTIONS` priority.

### Decisive source
```python
_INTENT_PATTERNS = {
    "commercial": {
        "patterns": [r"\b(best|top|vs|versus|compare|comparison|review|reviews|"
                     r"alternatives|features|pros and cons| which is better|" ...)\b"],
        "schema_required": {"Product", "Article", "FAQPage", "HowTo"},
        "weight": 1.2,
    }, ...
}
# bilingual by design: every pattern list mixes EN and IT triggers
# ("miglior|migliore|confronto|recensione|pro e contro")
```

**Flow:** extract heading/title/meta text once → `_score_text_for_intents` matches each family, collecting matched signals → `_check_schema_for_intent` verifies ANY of the intent's required schema types is present (`schema.found_types`) → coverage estimate combines signal count + schema-ok with the intent weight → primary intent = max estimated coverage; gaps summarized; recommendations generated for missing intents; radar data emitted for UI charts.
**Invariant:** Pattern hits alone don't make an intent "covered" — schema support gates full credit because AI engines preferentially cite pages whose structured data matches the query intent; weights are config-level constants inside the module table so tuning never touches logic. Zero HTTP fetches.
**Probe:** `tests/test_intent_mapping.py::test_commercial_weighted_highest` (+ coverage/schema-gating suites; `PYTHONPATH=src pytest tests/test_intent_mapping.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "intent mapping coverage schema", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the taxonomy-table + schema-gated coverage shape for any content-classification rubric; adapt intents/patterns/weights; omit radar/UI serialization if headless.
