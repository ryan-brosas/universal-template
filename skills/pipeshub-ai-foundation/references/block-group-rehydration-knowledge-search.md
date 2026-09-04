<!-- capsule-v2 -->
|# Block-group rehydration in knowledge search — when a hit IS a group (table/list/code), how do its children become individually citable results without re-indexing?

**Source:** pipeshub-ai Apache-2.0 `main@68509725e15c`; Codebase Memory project `pipeshub-ai`. **Question:** Search indexes embed whole block GROUPS, but citations need per-child granularity — where does the group get re-materialized and spliced back into the result stream?

## isBlockGroup hits re-materialize from blob storage, flatten, then TABLE/valid-group children splice in as first-class results
**Path/Symbol:** `backend/python/app/modules/retrieval/retrieval_service.py:search_with_filters` knowledge branch L513–522; location injection L664–672; flattening splice L681–691; final sort L693–697; helpers `get_record` / `get_flattened_results` imported from `app/utils/chat_helpers.py` (L38–42).
**Signature:** branch condition `knowledge_search: bool` parameter; `get_record(virtual_id, virtual_record_id_to_record, self.blob_store, org_id, virtual_to_record_map)` (mutates the dict); `get_flattened_results(new_type_results, blob_store, org_id, is_multimodal_llm=False, virtual_record_id_to_record, from_retrieval_service=True)`.
**Data Shape:** result metadata flag `isBlockGroup` (presence check `is not None`, not truthiness); flattened entries carry `block_type`; TABLE/valid-group content is a TUPLE `(summary, child_results)`; valid_group_labels = LIST/ORDERED_LIST/FORM_AREA/INLINE/KEY_VALUE_AREA/TEXT_SECTION/CODE (module constants L61–69).

### Decisive source
```python
if knowledge_search:
    meta = result.get("metadata")
    is_block_group = meta.get("isBlockGroup")
    if is_block_group is not None and virtual_id not in virtual_record_id_to_record:
        await get_record(virtual_id, virtual_record_id_to_record,
                         self.blob_store, org_id, virtual_to_record_map)
        record = virtual_record_id_to_record[virtual_id]
        if record is None:          # blob rehydration failed ⇒ drop THIS result
            continue                # (never fabricate children from nothing)
        new_type_results.append(result)
        continue                    # groups never enter final results directly
...
if new_type_results:
    flattened_results = await get_flattened_results(
        new_type_results, self.blob_store, org_id, False,
        virtual_record_id_to_record, from_retrieval_service=True)
    for result in flattened_results:
        block_type = result.get("block_type")
        if block_type == GroupType.TABLE.value or block_type in valid_group_labels:
            _, child_results = result.get("content")     # tuple: (summary, children)
            for child in child_results:
                final_search_results.append(child)       # children are citable rows
        else:
            final_search_results.append(result)          # plain blocks pass through
```
(L513–522, L681–691.)

**Flow:** hybrid hits flagged isBlockGroup → per-virtual-id ONCE memoization via `virtual_record_id_to_record` (several chunks of one group share one blob read) → blob-store rehydration (None ⇒ skip) → after enrichment, ALL collected groups flatten → group-typed entries split into their children, everything else passes through → global score-desc sort → required_fields citation filter applies to children like any other result.
**Invariant:** (1) Flag presence (`is not None`) gates the branch — an explicit False must reach final results untouched (branch test test_knowledge_search_is_block_group_none_goes_to_final :1469–1496 pins metadata WITHOUT the flag going to final). (2) Rehydration is memoized per virtual id inside the request; a failed blob read yields NO children rather than a half-citable group (:1211–1252). (3) Only TABLE + the seven declared group labels unpack `(summary, children)` tuples — the tuple contract would crash on anything else that sneaks in with tuple content. (4) Children inherit full citation metadata because they were embedded WITH it at index time; retrieval only splits, never reconstructs. (5) The final sort is global across spliced children and plain results, so ranking stays comparable.
**Probe:** EXECUTED at pin: combined battery 124 passed rc=0 (/tmp/psh21venv). Decisive tests: test_knowledge_search_with_block_groups :1128–1208 (mocked get_record/get_flattened_results; asserts "table row content" AND "text result" both in searchResults), test_knowledge_search_get_record_returns_none_skips :1211–1252, TestSearchWithFiltersBranches.test_knowledge_search_is_block_group_none_goes_to_final :1469–1496. Anchor greps verified pre-write: `isBlockGroup` :515, `required_fields` :700.
**Retrieve:** EXECUTED live — mcp__codebase-memory__search_graph project=`pipeshub-ai` file_pattern=`*.py` query="isBlockGroup get_flattened_results knowledge search block group table children" → resolves TestSearchWithFiltersBranches.test_knowledge_search_is_block_group_none_goes_to_final and the sibling table-children suites.

## Verdict
Adopt for any index that embeds composite units but cites leaves: flag-presence gating, per-id memoized rehydration, None-means-skip, typed tuple-unpack splice, then one global sort. Adapt the group-label set to your block taxonomy. Omit the memo dict only if your flatten helper already dedupes by id upstream.
