<!-- capsule-v2 -->
|# Retrieval limit budget divisor cap — how do you split one result budget across N sources without letting N drive per-source limits to noise?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** A tool searches 1..N knowledge sources with a fixed global block budget — what's the limit formula, and which count does the budget key off when filters are synthetic?

## 50-or-100÷min(N,5) internal budget, never a model-supplied limit
**Path/Symbol:** `backend/python/app/agents/actions/retrieval/retrieval.py` `_MAX_RETRIEVAL_SOURCES_DIVISOR = 5` (:45), budget computation :370–376, trim :546–551; placeholder counting via base_scope built from state apps/kb :342–356.
**Signature:** `adjusted_limit = 50 if total_sources <= 1 else 100 // min(total_sources, _MAX_RETRIEVAL_SOURCES_DIVISOR)`.
**Data Shape:** `total_sources = len(base_scope.app_ids) + len(base_scope.kb_ids)` — computed from the AGENT'S scope (curated filters, or state apps/kb for placeholder agents), never from the LLM's per-call connector_ids.

### Decisive source
```python
# Cap the divisor to prevent excessively small per-source limits when many
# knowledge sources are configured simultaneously.
_MAX_RETRIEVAL_SOURCES_DIVISOR = 5
...
agent_connector_ids_count = len(base_scope.app_ids)
agent_collection_ids_count = len(base_scope.kb_ids)
total_sources = agent_connector_ids_count + agent_collection_ids_count
if total_sources <= 1:
    adjusted_limit = 50
else:
    adjusted_limit = 100 // min(total_sources, _MAX_RETRIEVAL_SOURCES_DIVISOR)
```
(:43–45, :370–376.) The tool exposes NO limit parameter to the model at all; the trim keeps `final_results[:adjusted_limit]` only on the combined path (:550–551) because fan-out legs were each already allocated the same budget.

**Flow:** scope counts come from agent config → single/zero sources get a fat 50 → multi-source splits 100 across sources but the divisor saturates at 5, so ≥5 sources all get floor 20 → fan-out reuses the SAME adjusted_limit as each leg's allocation; combined path trims to it after ranking.
**Invariant:** (1) The model cannot raise the budget: there is no limit parameter in SearchInternalKnowledgeInput. (2) The budget keys off CONFIGURED scope, not requested ids — a narrow filter must not unlock a bigger share. (3) Divisor saturation bounds worst-case shrinkage (100//min(N,5) ⇒ minimum 20); without it 30 sources would search 3 blocks each. (4) Placeholder agents' synthetic empty filters would compute total=0 ⇒ 50 — tests pin that state apps/kb counts are used instead (:571–587).
**Probe:** EXECUTED at pin: test_retrieval.py::TestSearchInternalKnowledge.test_results_trimmed_to_adjusted_limit :270–294 (150 results trimmed, header "Top 50 blocks"), test_limit_computed_internally :333–347 (limit ≤100); test_retrieval_extended.py::TestLimitAdjustedByScope.test_limit_divided_by_scope_count :641–656 (2 apps+3 kbs ⇒ limit==100//5==20), TestPlaceholderLimitUsesStateScopeCounts :570–587.
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` file_pattern=`*agents/actions/retrieval*` query="adjusted limit sources divisor per source retrieval budget" → resolves the owning class surface (search_internal_knowledge rank 3 with the constant defined at module top); the constant itself is a module var, so the budget tests are the decisive anchors.

## Verdict
Adopt the saturated-divisor budget whenever one tool fans a fixed context budget over a variable source count. Adapt the 50/100 constants and saturation point to your token economics. Omit the placeholder branch only if your agents can never present an empty configured-scope set.

<!-- capsule-evidence: pipeshub-ai@68509725e15c retrieval.py L43–45/L370–376/L546–551; four direct tests; live search_graph 2026-08-26 -->
