<!-- capsule-v2 -->
# Search facade — dataset fan-out, backwards-compatible result shapes

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does one search call fan out across datasets with per-dataset DB context, then return a shape old callers can still parse?

## search → authorized_search → search_in_datasets_context
**Path/Symbol:** `cognee/modules/search/methods/search.py:search` (:53-152), `search_in_datasets_context` (:215-409), `_backwards_compatible_search_results` (:412-464); retriever factory `get_search_type_retriever_instance.py:get_search_type_retriever_instance` (:54-422).
**Signature:** `async search(query_text, query_type, dataset_ids, user, ..., top_k=15, node_type=NodeSet, include_references=False, ...) -> List[SearchResult]`.
**Data Shape:** Per-dataset `SearchResultPayload{result_object, context, completion, search_type, only_context, dataset_name/id/tenant_id}`; legacy output = `{dataset_id, dataset_name, dataset_tenant_id, search_result|text/context/objects_result}` dicts.

### Decisive source
```python
soften_code_seed_misses = query_type is SearchType.CODE and len(search_datasets) > 1
for dataset in search_datasets:
    tasks.append(_search_in_dataset_context(dataset=dataset, ...))
    if soften_code_seed_misses:
        # A name/id seed one dataset cannot resolve says nothing about the others:
        tasks[-1] = _report_code_seed_miss(tasks[-1], dataset)
        # → SearchResultPayload(result_object=None,
        #    completion={"seed_not_found": True, "error": str(error)}, ...)
return await asyncio.gather(*tasks)

# history logged AFTER the search — only the results reveal which datasets were
# actually searched; completion text only (raw results run 50-100 KB each):
await log_search_history(query_text, query_type.value, user.id, search_results)
```

**Flow:** authorize datasets (`None` ⇒ all read-accessible) → per dataset: set_database_global_context_variables(dataset.id, owner_id) THEN empty-graph warnings (distinguishing "has data but no cognify" from "nothing added") → retriever instance from the registry (top_k ≤ 0 rejected; skills/tools keys ONLY legal on AGENTIC_COMPLETION; CYPHER/NATURAL_LANGUAGE gated by ALLOW_CYPHER_QUERY) → gather → shape-compat projection (verbose vs `.result`; single-element list unwrapped in non-backend mode).
**Invariant:** (1) Multi-dataset CODE searches must NOT fail wholesale on one seed miss — per-dataset softening. (2) The registry maps SearchType → (class, kwargs); FEELING_LUCKY resolves BEFORE factory use via `select_search_type`. (3) Back-compat layer is the ONLY place allowed to drop search_type.
**Probe:** `cognee/tests/unit/modules/search/test_search_result_payload.py`; retriever wiring tests under `cognee/tests/unit/modules/retrieval/`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "search_in_datasets_context authorized_search _backwards_compatible_search_results", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt context-scoped fan-out + per-dataset failure softening + explicit back-compat projection; adapt permission checks and payload fields to your API; omit telemetry/history specifics.
