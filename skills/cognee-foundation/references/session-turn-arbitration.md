<!-- capsule-v2 -->
# Session-aware completion — turn arbitration and access-timestamp tracking

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does a retriever decide whether to answer at all on a session turn, and how do retrieved elements feed back into data-freshness signals?

## GraphCompletionRetriever.get_completion + access_tracking
**Path/Symbol:** `cognee/modules/retrieval/graph_completion_retriever.py:get_completion` (:425-466), `get_completion_from_context` (:368-423); `cognee/modules/retrieval/utils/access_tracking.py:update_node_access_timestamps` (:19-42), `_find_origin_documents_via_projection` (:45-71).
**Signature:** `get_completion(query=None, query_batch=None) -> List[Any]`; gate = `prepare_session_turn_for_retrieval(query)`.
**Data Shape:** TurnPreparation carries `{should_answer, response_to_user, effective_query}`; session path requires `user.id and CacheConfig().caching and not query_batch`.

### Decisive source
```python
turn_preparation = await self.prepare_session_turn_for_retrieval(query)
if not turn_preparation.should_answer:
    return [turn_preparation.response_to_user or "Got it."]   # NO retrieval runs
effective_query = turn_preparation.effective_query or query
# ... retrieval + context + completion with effective_query threaded through ...

# access tracking (ENABLE_LAST_ACCESSED, default false): project the WHOLE graph
# with minimal props, walk chunk→document edges in memory:
memory_fragment.project_graph_from_db(graph_engine,
    node_properties_to_project=["id", "type"],
    edge_properties_to_project=["relationship_name"])
...
if neighbor.get_attribute("type") in ["TextDocument", "Document"]:
    doc_ids.add(neighbor.id)
await session.execute(update(Data).where(Data.id.in_([...])).values(last_accessed=now))
```

**Flow:** validate → turn gate (short-circuit before ANY retrieval when the arbiter says don't answer — e.g. acknowledgements) → retrieve → context → completion; session path funnels through `generate_completion_with_session` with `used_graph_element_ids` extracted from edges; both branches REJOIN at `append_references` so evidence appends exactly once. References are grounded by re-searching the ANSWER TEXT against chunks ("Evidence bullets reflect where the answer is grounded rather than which graph elements happened to be retrieved") and only for plain-string completions.
**Invariant:** (1) The should-answer gate precedes retrieval — answering costs nothing when declining. (2) Evidence must never corrupt structured `response_model` outputs. (3) Access timestamps are opt-in and document-scoped: node ids map back to origin documents via projection, then ONE bulk SQL update.
**Probe:** `cognee/tests/unit/modules/retrieval/test_concurrent_turn.py`, `test_concurrent_turn_eligibility.py`, `test_access_tracking.py`, `test_include_references_wiring.py`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "prepare_session_turn_for_retrieval update_node_access_timestamps append_references", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pre-retrieval turn arbitration and rejoining reference-append; adapt the arbiter policy to your product; omit whole-graph-projection access tracking on large graphs (cost scales with graph size).
