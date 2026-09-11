<!-- capsule-v2 -->
# Update-chain workflow plane — three-provider merges, state-key handoffs, and hrid continuation

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory project `graphrag`. **Question:** How do the eight `update_*` steps coordinate — who reads which provider, how do ids continue across runs, and in what order must the chain run?

## Key facts
**Path/Symbol:** provider triple from `graphrag/index/run/utils.py get_update_table_providers` (:59-75): output / previous / delta via `table_provider.child(timestamp)` → `.child("previous"|"delta")` (Cosmos namespace isolation vs filesystem child paths). Steps: `update_final_documents.py` (:27-32 concat_dataframes), `update_entities_relationships.py` (:61-119 merge → filter_orphan_relationships :85-87 → re-summarize via extract_graph's OWN `get_summarized_entities_relationships` :99-111), `update_communities.py` (:40-54 mapping out), `update_community_reports.py` (:31 mapping in, :48-67), `update_text_units.py` (`_update_and_merge_text_units` :63-95), `update_covariates.py` (:56-80 same pattern), `update_text_embeddings.py` (delegates to generate_text_embeddings on OUTPUT provider), `update_clean_state.py` (:19-31 prefix sweep).
**Signature:** every step: `(output_table_provider, previous_table_provider, delta_table_provider) = get_update_table_providers(config, context.state["update_timestamp"])`.
**Data Shape:** id-continuation contract: delta rows get NEW human_readable_ids starting at `old.max() + 1`; entity identity remap travels as `incremental_update_entity_id_mapping` (old→merged id dict) applied to delta text_units' `entity_ids` lists.

### Decisive source
```python
# update_text_units.py :85-93 — remap THEN renumber THEN concat:
if entity_id_mapping:
    delta_text_units["entity_ids"] = delta_text_units["entity_ids"].apply(
        lambda x: [entity_id_mapping.get(i, i) for i in x] if x is not None else x)
initial_id = old_text_units["human_readable_id"].max() + 1     # continuation, never restart at 0
delta_text_units["human_readable_id"] = np.arange(initial_id, initial_id + len(delta_text_units))
return pd.concat([old_text_units, delta_text_units], ignore_index=True)
```
```python
# update_clean_state.py :22-28 — terminal sweep makes the state namespace self-cleaning;
# the #noqa: RUF029 marks the deliberately un-awaited async fn (nothing to await)
keys_to_delete = [k for k in context.state if k.startswith("incremental_update_")]
```
**Flow (pipeline ORDER is semantic):** load_update_documents (stop-if-empty) → base standard/fast flows rebuild DELTA artifacts → update_final_documents → update_entities_relationships (produces entity mapping; orphans filtered against MERGED entities) → update_text_units (consumes mapping) → update_covariates → update_communities (produces community mapping) → update_community_reports (consumes it) → update_text_embeddings (re-embed merged output) → update_clean_state.
**Invariant:** merge products travel through `context.state` keys, never return values; orphan filtering happens AFTER merging but BEFORE summarization/re-embedding; human_readable_id streams NEVER reset across updates (query caches assume monotonic ids); covariates skip silently when either side lacks the table (:31-33 double has-check).
**Probe:** `tests/unit/indexing/update/test_update_relationships.py` (:68 merges old+delta, :83 overlapping-pairs aggregate, :96 hrid increment, :120/:139/:158 orphan source/target/both); verbs-level `tests/verbs/test_update_text_embeddings.py`; run_pipeline-level delta/previous layout pinned in tests cited by incremental-pipeline capsule.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "graphrag", query: "get_update_table_providers _update_and_merge incremental_update_entity_id_mapping", limit: 10 })`

## Verdict
Adopt timestamped three-provider isolation, explicit state-key handoff objects, max+1 id continuation, and a terminal cleanup sweep. The chain order above IS the porting spec — reordering breaks producer-before-consumer dependencies.
