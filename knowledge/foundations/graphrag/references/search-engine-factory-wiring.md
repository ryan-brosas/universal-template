<!-- capsule-v2 -->
# Search-engine factory wiring — how does config select per-mode models and where do the DEFAULT context-builder params live (not in the builders)?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** what exactly does each get_*_search_engine constructor wire, and which hardcoded defaults would a porter wrongly read from config?

## four factory functions
**Path/Symbol:** `packages/graphrag/graphrag/query/factory.py` (`get_local_search_engine` :37-100, `get_global_search_engine` :103-180 incl. dynamic-selection kwargs :128-142, `get_drift_search_engine` :183-227, `get_basic_search_engine` :230-275).
**Signature:** `get_X_search_engine(config, <tables>, description_embedding_store?, response_type, system_prompt?, callbacks?) -> LocalSearch | GlobalSearch | DRIFTSearch | BasicSearch`.
**Data Shape:** every engine gets the SAME tokenizer instance as its context builder (`tokenizer = chat_model.tokenizer` shared) so token budgeting matches the actual model.

### Decisive source
```python
# factory.py:84-97 — LOCAL's builder params are HARDCODED policy here,
# not config fields: rank/weight inclusion flags and user-turns-only
# history live in code; only the numeric budgets come from ls_config
context_builder_params={
    "text_unit_prop": ls_config.text_unit_prop,
    "community_prop": ls_config.community_prop,
    "conversation_history_max_turns": ls_config.conversation_history_max_turns,
    "conversation_history_user_turns_only": True,
    "top_k_mapped_entities": ls_config.top_k_entities,
    ...
    "include_entity_rank": True, "include_relationship_weight": True,
    "include_community_rank": False, "return_candidate_context": False,
    "embedding_vectorstore_key": EntityVectorStoreKey.ID,
```
```python
# :129-142 — dynamic community selection REUSES THE SAME completion model
# for rating (TODO admits a -mini model wish); concurrent_coroutines comes
# from TOP-LEVEL config.concurrent_requests, not global_search section
if dynamic_community_selection:
    dynamic_community_selection_kwargs.update({
        "model": model, "tokenizer": tokenizer,
        "keep_parent": gs_config.dynamic_search_keep_parent,
        "concurrent_coroutines": config.concurrent_requests, ...})
```

**Flow:** resolve named model config via `config.get_completion_model_config(config.X.completion_model_id)` → `create_completion/create_embedding` (graphrag_llm factories) → construct context builder with tables + store + tokenizer → construct engine with prompts (None = engine default), `model_params=model_settings.call_args`, and the param dict above. DRIFT takes NO context_builder_params dict — its builder consumes `config.drift_search` directly.
**Invariant:** `EntityVectorStoreKey.ID` is chosen in TWO places per engine (:78 constructor AND :95 params dict) — the comments say switch both to TITLE if your vectorstore indexes titles; missing either one desyncs entity mapping. Global hardcodes `use_community_summary: False`, `shuffle_data: True`, `json_mode=False` — porters copying settings.yaml expectations miss these are code-owned.
**Probe:** no dedicated unit file (factories exercised through query-context unit tests); pinned @pin by greps: `grep -c 'EntityVectorStoreKey.ID' query/factory.py` = 2, `grep -c 'dynamic_community_selection_kwargs' query/factory.py` = 3, `grep -c 'get_completion_model_config' query/factory.py` = 4. Recorded caveat: verified by direct read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "get local search engine context builder params config", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared-tokenizer rule, two-site vectorstore-key selection, and the split of numeric-budgets-in-config vs policy-flags-in-code; adapt defaults to host; omit dynamic-selection plumbing if you don't port LLM-rated community preselection.
