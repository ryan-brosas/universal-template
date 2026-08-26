<!-- capsule-v2 -->
# LocalSearchMixedContext — how does entity-grounded retrieval compose a token-budgeted prompt context from vector-matched entities?

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** given a query, how are entities selected by vector similarity and then expanded outward (reports → relationships → covariates → sources) under one token budget — and what breaks if you port the budget math wrong?

## Vector-seeded mapping + proportional slice budget
**Path/Symbol:** `packages/graphrag/graphrag/query/structured_search/local_search/mixed_context.py:54-222` (`LocalSearchMixedContext.__init__` :57-89, `build_context` :91-222); `query/context_builder/entity_extraction.py:41-96` (`map_query_to_entities`, `EntityVectorStoreKey` ID/TITLE).
**Signature:** `build_context(query, conversation_history=None, ..., max_context_tokens=8000, text_unit_prop=0.5, community_prop=0.25, top_k_mapped_entities=10, top_k_relationships=10, include_entity_rank=False, return_candidate_context=False) -> ContextBuilderResult(context_chunks, context_records)`.
**Data Shape:** constructor holds every table as id-keyed dicts (entities, community_reports keyed by `community_id`, text_units, relationships; covariates as dict-of-lists). Result chunks are `-----Name-----` pipe-tables joined `\n\n`; records are DataFrames per section.

### Decisive source
```python
# mixed_context.py:125-137 — guard + history-augmented embedding query
if community_prop + text_unit_prop > 1:
    raise ValueError("The sum of community_prop and text_unit_prop should not exceed 1.")
if conversation_history:
    pre_user_questions = "\n".join(conversation_history.get_user_turns(...))
    query = f"{query}\n{pre_user_questions}"          # history rides INTO the vector match
# :139-149  oversample 2x so excludes don't shrink the pool
selected_entities = map_query_to_entities(..., k=top_k_mapped_entities, oversample_scaler=2)
```
```python
# entity_extraction.py:59-82 — empty query falls back to rank-sorted entities
search_results = text_embedding_vectorstore.similarity_search_by_text(
    text=query, text_embedder=lambda t: text_embedder.embedding(input=[t]).first_embedding,
    k=k * oversample_scaler)
...   # else: all_entities.sort(key=lambda x: x.rank or 0, reverse=True); take [:k]
```
**Flow:** slice budget FIRST: history tokens deducted from `max_context_tokens`; remaining split proportionally — `community_tokens = N*community_prop`, `local_prop = 1 - community_prop - text_unit_prop`, `text_unit_tokens = N*text_unit_prop` (:175-208). Then compose outward: community reports → entity/relationship/covariate tables → text units. `map_query_to_entities` embeds the (history-joined) query, oversamples 2×k, resolves store ids back to entities (uuid-with/without-dashes tolerant), filters excludes, prepends includes.
**Invariant:** every table consumes its slice until cap and STOPS (`break` on first over-budget row); ordering is specificity-first — entities before relationships before reports/text units. Porters get this wrong by re-normalizing props or letting later tables steal earlier slices.

## Add-one-entity revert loop (the local table builder)
**Path/Symbol:** `_build_local_context` `mixed_context.py:377-493`; `_filter_relationships` `context_builder/local_context.py:232-317`.
**Signature:** iterates `selected_entities`, rebuilding relationship+covariate context after EACH added entity.
**Data Shape:** relationship ranking: in-network first (both endpoints selected), then out-network sorted by `(links, rank|weight)` desc; budget = `top_k_relationships * len(selected_entities)`.
### Decisive source
```python
# mixed_context.py:448-455 — whole-candidate revert, never partial trim
if total_tokens > max_context_tokens:
    logger.warning("Reached token limit - reverting to previous context state")
    break
final_context = current_context        # only committed if the WHOLE entity fits
final_context_data = current_context_data
```
```python
# local_context.py:296-301 — out-network priority = mutual-link count × rank
out_network_relationships.sort(key=lambda x: (x.attributes["links"], x.rank), reverse=True)
```
**Flow:** for each candidate entity: rebuild rel+covariate context with all entities so far → if total exceeds the slice, revert to previous state and stop; else commit. Community reports rank by `(matched-entity count, rank)` with a temporary `attributes["matches"]` injected and DELETED after sort (:257-263); text units sort `(entity_order asc, -num_relationships)` (:341) via `count_relationships` (`source_context.py:82-100`: set-based when `text_unit.relationship_ids` exists, else scan `rel.text_unit_ids`).
**Invariant:** the local block is atomic per entity — an entity is fully in or fully out with its relationships/covariates. NOTE the asymmetry: community `matches` attr is cleaned up, but `_filter_relationships`'s injected `attributes["links"]` is NOT removed before serialization (:287-294).
**Probe:** no dedicated unit test pins `LocalSearchMixedContext` itself (mode tests live at smoke/integration level — coverage caveat). Direct neighbors on disk: `tests/unit/query/context_builder/test_entity_extraction.py::test_map_query_to_entities` :97-166 (pins TITLE-key matching AND the empty-query→rank-fallback), `tests/unit/query/input/retrieval/test_entities.py::test_get_entity_by_id/by_key` :11-167 (pins uuid dash/no-dash resolution).

## Candidate-context tagging (`return_candidate_context`)
**Path/Symbol:** `mixed_context.py:280-303,354-373,461-489`; `get_candidate_context` `local_context.py:320-357`.
**Signature:** when enabled, builders ALSO return candidates that didn't fit, each DataFrame gaining an `in_context` bool column.
**Flow:** if a section's key already has in-window rows, mark candidates `in_context = id.isin(window_ids)`; else attach full candidate frame tagged False. Debugging/export surface — omit for minimal ports.
**Probe:** same caveat as above (no dedicated unit test).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "LocalSearchMixedContext build_context map_query_to_entities _filter_relationships", limit: 10, fields: ["signature", "name", "file"] });
// trace: graphrag.packages.graphrag.graphrag.query.structured_search.local_search.mixed_context.LocalSearchMixedContext.build_context (53 outbound callees incl. build_community_context, ConversationHistory.build_context, VectorStore.similarity_search_by_text)
```

## Verdict
Adopt vector-seeded entity mapping with 2× oversample + include/exclude lists, proportional slice budgeting with the prop-sum guard, add-one-entity revert commitment, in/out-network relationship prioritization, and `in_context` candidate tagging; adapt default proportions/budgets, key choice (ID vs TITLE), and rank attributes to host; omit covariates if claims aren't modeled. Coverage caveat: search-mode orchestration itself is smoke/integration-tested only; the cited unit tests pin the entity-mapping helpers, not the builder.
