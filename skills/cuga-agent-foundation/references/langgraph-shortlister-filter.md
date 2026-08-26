<!-- capsule-v2 -->
# ShortlisterAgent name-space filter — how do shortlisted names become executable tool specs without trusting the LLM?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How is an LLM's free-form shortlist projected onto the cached catalogue, and why is the filter applied twice per subtask?

## Catalogue-projected selection, filtered at both stages
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/api/shortlister_agent/shortlister_agent.py:ShortlisterAgent.filter_by_api_names` (:58-81), `get_function_names` (:40-51), `run` (:83-98); call site `api_planner.py` :234-240.
**Signature:** `filter_by_api_names(data: dict, target_api_names: list) -> dict` over `{app_name: {api_id: {app_name, api_name, ...}}}`.
**Data Shape:** `ShortListerOutput.result = List[APIDetails]` (name+reasoning); Lite variant repacks `thoughts=[]`. Cache input `state.api_shortlister_all_filtered_apis` holds FULL tool schemas keyed app→api_id.

### Decisive source
```python
    @staticmethod
    def filter_by_api_names(data: dict, target_api_names: list) -> dict:
        result = {}
        for app_name, apis in data.items():
            matched_apis = {
                api_id: api_details
                for api_id, api_details in apis.items()
                if api_details.get("api_name") in target_api_names
            }
            if matched_apis:
                result[app_name] = matched_apis
        return result
```
planner re-filter after the coder action:
```python
            state.api_shortlister_planner_filtered_apis = json.dumps(
                ShortlisterAgent.filter_by_api_names(
                    state.api_shortlister_all_filtered_apis,
                    [api.api_name for api in res.action_input_coder_agent.relevant_apis],
                ),
                indent=2,
            )
```

**Flow:** node composes `shortlister_query` ("**Input task**: …\n\nTask context:{sub_task}") → agent invokes chain with `json.dumps(apis, indent=2)` of the whole current-app catalogue → LLM returns APIDetails names → projection keeps ONLY catalogue entries whose `api_name` matches (hallucinated names vanish silently) and drops apps left empty → planner stage later narrows again to the coder action's `relevant_apis`.
**Invariant:** The LLM output is NEVER executed or embedded verbatim — it's a name set intersected against ground-truth schemas. Empty apps are omitted entirely (`if matched_apis`), not rendered as empty maps. This is the LangGraph-plane complement to the pass-18 TOML-strategy shortlister seam (#624): same cap discipline, different retrieval mechanism.
**Probe:** Sibling direct tests pin the strategy-plane twin (`tests/unit/test_shortlister_name_validation.py`, `tests/unit/test_shortlister_config_surfaces.py`). Deterministic here: `grep -n "filter_by_api_names" src/cuga/backend/cuga_graph/nodes/api/api_planner.py` hits the :235 call.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ShortlisterAgent filter_by_api_names get_function_names APIDetails", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt select-then-intersect-with-catalogue as the trust boundary for any LLM curation step; adopt two-stage filtering (shortlist for context, re-filter for execution). Adapt the cache key layout to your state shape. Omit the thoughts/Lite repack if your models always emit structured thoughts.
