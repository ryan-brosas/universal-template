<!-- capsule-v2 -->
|# Permission-first search ladder — how does semantic search stay leak-proof when the vector store, the record store, and the permission graph are three different systems?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** In what ORDER must accessible-ids resolution, vector filtering, and record fetching run so no chunk a user cannot see can ever surface — even when several connectors share one virtualRecordId?

## Resolve the accessible virtualRecordId→recordId map BEFORE searching; filter with must=; fetch only permission-verified ids
**Path/Symbol:** `backend/python/app/modules/retrieval/retrieval_service.py:RetrievalService.search_with_filters` (L326–746 direct HEAD read; None-limit normalization L343–353; init gather L362–366; must-filter L382–391; leakage guard comment+resolution L409–417; typed error tails L733–746); status→HTTP `_create_empty_response` L866–886.
**Signature:** `search_with_filters(queries, user_id, org_id, filter_groups=None, limit=20, virtual_record_ids_from_tool=None, knowledge_search=False, time_range=None) -> dict` (searchResults/records/status/status_code/message/virtual_to_record_map).
**Data Shape:** accessible map `{virtualRecordId: recordId}` from `graph_provider.get_accessible_virtual_record_ids`; vector filter `must={"orgId": org_id, "virtualRecordId": [...accessible or tool ids...]}`; empty responses carry enum `Status` + mapped HTTP (ACCESSIBLE_RECORDS_NOT_FOUND→404, VECTOR_DB_EMPTY/NOT_READY→503, EMPTY_RESPONSE→200, ERROR→500).

### Decisive source
```python
if limit is None:                       # prefetch forwards request limit verbatim;
    limit = DEFAULT_SEARCH_LIMIT        # explicit None beat the default arg and
                                        # died at req.limit*2 inside qdrant/utils,
                                        # swallowed as "Filtered search failed" =>
                                        # answer with NO context and NO visible error
accessible_virtual_id_to_record_id, user = await asyncio.gather(
    self._get_accessible_virtual_record_ids_task(...),   # PERMISSION MAP FIRST
    self._get_user_cached(user_id))
if not accessible_virtual_id_to_record_id:
    return self._create_empty_response(..., Status.ACCESSIBLE_RECORDS_NOT_FOUND)  # 404
filter = await self.vector_db_service.filter_collection(
    must={"orgId": org_id,
          "virtualRecordId": list(accessible_virtual_id_to_record_id.keys())})
...
# "Resolve only the permission-verified recordIds for the returned virtual IDs.
#  This prevents cross-connector leakage: if multiple connectors share the same
#  virtualRecordId, we only fetch the specific record the user has access to."
record_ids_to_fetch = list({accessible_virtual_id_to_record_id[vid]
                            for vid in returned_virtual_record_ids
                            if vid in accessible_virtual_id_to_record_id})
```
(L343–353, L362–371, L382–391, L409–417.)

**Flow:** require graph_provider → normalize None-limit → gather(accessible-map, cached-user) → empty map ⇒ 404 envelope → build must-filter over accessible ids (or tool-supplied ids) → hybrid search → extract returned virtualRecordIds → INTERSECT with the permission map → fetch exactly those records → enrich metadata → sort/filter → response. Failure tails: VectorDBEmptyError ⇒ 503 envelope; ValueError ⇒ bad-request envelope; generic exception ⇒ error envelope, EXCEPT tool-id callers get `{}` (falsy = no-results for agent mode).
**Invariant:** (1) The vector filter is MUST over orgId AND the pre-resolved accessible id set — the store itself cannot return invisible chunks; post-filters would be too late. (2) Record fetching intersects returned ids with the permission map — shared virtualRecordIds across connectors resolve only to the permitted record. (3) Optional params forwarded verbatim by middle layers defeat Python default-args: normalize explicit None explicitly (the inline incident comment + regression test :579–598 pin this). (4) Every terminal path returns a TYPED envelope (status enum + HTTP code) — never a naked raise toward users; agent-mode tool paths contract on falsy instead. (5) Missing graph_provider is an immediate ERROR envelope (:559–564).
**Probe:** EXECUTED at pin: combined battery 124 passed rc=0 (/tmp/psh21venv). Decisive tests: test_explicit_none_limit_falls_back_to_the_default :579–598 (docstring restates the incident; asserts passed_limit == DEFAULT_SEARCH_LIMIT), test_returns_404_when_no_accessible_records :567–576, test_tool_provided_virtual_ids_use_must_filter :800–813 ("must" not "should"), test_generic_exception_with_tool_ids_returns_empty_dict :752–764, test_raises_when_no_graph_provider :559–564, test_vector_db_empty_error_non_agent :731–739. Anchor greps verified pre-write: DEFAULT_SEARCH_LIMIT :52/:353.
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` file_pattern=`*modules/retrieval/*` query="search_with_filters accessible virtual record ids permission" → resolves `search_with_filters` + `_get_accessible_virtual_ids_task` + mapping tests.

## Verdict
Adopt the ordering (permission map → must-filter → intersect → fetch) verbatim for any cross-store RAG surface; adopt the typed empty-envelope status→HTTP map for API symmetry. Adapt the id namespaces (virtualRecordId/recordId) to your domain pair. Omit nothing in the order — moving intersection before filtering re-introduces the cross-connector leak the comment documents.
