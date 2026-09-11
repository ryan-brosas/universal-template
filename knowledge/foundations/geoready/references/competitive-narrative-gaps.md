<!-- capsule-v2 -->
# Competitive narrative & gap analysis — LLM competitor summaries with prompt sanitization, deterministic gaps

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you combine optional LLM narration with deterministic gap math without letting the LLM invent facts?

## Sanitized prompt input + rule-built gap actions sorted by impact
**Path/Symbol:** `src/geo_optimizer/core/competitive_narrative.py:_sanitize_prompt_input` (46–62), `run_competitive_narrative_analysis` (252+), `_build_competitive_gaps` (320+); `src/geo_optimizer/core/gap_analysis.py:build_gap_analysis` (18–44).
**Signature:** `run_competitive_narrative_analysis(url, brand, audit, provider, api_key, model) -> CompetitiveNarrativeResult`; `build_gap_analysis(result1, result2) -> GapAnalysisResult`.
**Data Shape:** `CompetitorNarrative(summary, strengths, weaknesses)` from LLM; `CompetitiveGap(category, url_gap, competitor_advantage, action, priority, impact_points)` purely computed; gap analysis sorts weaker/stronger by score then builds an action plan per category.

### Decisive source
```python
def _sanitize_prompt_input(text: str, max_len: int = 500) -> str:
    """Strip control characters and cap length before any user/site-derived
    string enters a prompt — the page being audited is UNTRUSTED input."""
    ...
# Gap actions are DETERMINISTIC: derived from the two AuditResults'
# score_breakdowns (category deltas → recoverable points → priority ladder),
# never from the model's prose. The LLM only narrates strengths/weaknesses.
```

**Flow:** competitor audit runs first (reuse of the whole kernel) → narrative extraction feeds sanitized inputs to `query_llm` (error-as-value contract; failures degrade to empty narrative, not exception) → `_build_competitive_gaps` diffs category breakdowns into prioritized actions (`_priority_for_impact`: high ≥ some points threshold) → dedupe by category → summary blends counts; standalone `geo gap-analysis` path (`gap_analysis.py`) skips LLMs entirely and sorts sites by score to orient "weaker vs stronger".
**Invariant:** Facts (scores, gaps, priorities) come ONLY from deterministic diffing; the LLM contributes prose strictly bounded by sanitized inputs — a hostile competitor page cannot inject instructions through unsanitized text or fabricate its own advantages. Impact points derive from CATEGORY_MAX − earned, same recovery math as recommendations.
**Probe:** `tests/test_competitive_narrative.py::test_sanitize_prompt_input_strips_control_chars` (+ `tests/test_gap_analysis.py::test_action_plan_orders_by_impact` (`PYTHONPATH=src pytest tests/test_competitive_narrative.py tests/test_gap_analysis.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "competitive narrative sanitize", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt deterministic-facts/LLM-prose separation with prompt-input sanitization for any AI-assisted comparison feature; adapt categories; omit vendor prompt templates.
