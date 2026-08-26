<!-- capsule-v2 -->
# Node resolution & summary flights — LLM-confirmed merge + batched summarization

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does entity resolution confirm fuzzy candidates with an LLM, and how do node summaries update in bounded batches instead of one call per node?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/maintenance/node_operations.py` (1,032 lines): `resolve_extracted_nodes` (:627), `_collect_candidate_nodes` (:407), `_semantic_candidate_search` (:418), `_resolve_with_llm` (:467), `_merge_candidate_nodes` (:387), `_commit_resolution` (:453), `_collapse_exact_duplicate_extracted_nodes` (:336), `_extract_entity_summaries_batch` (:833), `_process_summary_flight` (:913-1006), `extract_attributes_from_nodes` (:726).
**Signature:** `_process_summary_flight(llm_client, nodes, episode, previous_episodes, *, use_episode_prompt=False, entity_types=None)` — builds ONE batch context for many nodes (`entities[]` with name/summary/labels/attributes) and issues a single extraction prompt per flight.
**Data Shape:** batch context `{entities: [{name, summary, entity_types, attributes}], episode_content, previous_episodes: [{content, timestamp}], entity_type_descriptions}` — type descriptions come from Pydantic docstrings with GOOD/BAD few-shot examples stripped (`_truncate_type_description`).

### Decisive source
```ts
async def _process_summary_flight(llm_client, nodes, episode, previous_episodes, *, use_episode_prompt=False, entity_types=None):
    # Build entity type descriptions from docstrings, stripping GOOD/BAD
    # few-shot examples that are intended for extraction prompts only.
    entities_context = [{'name', 'summary', 'entity_types', 'attributes'} for node in nodes]
    # ONE prompt for the whole flight; group_id taken from nodes[0] (batch invariant)
# Resolution path:
#   _collect_candidate_nodes -> _semantic_candidate_search (embedding top-k)
#     -> _resolve_with_llm (LLM confirms/denies each fuzzy candidate)
#     -> _merge_candidate_nodes -> _commit_resolution
```

**Flow:** exact duplicates collapse first (`_collapse_exact_duplicate_extracted_nodes`) → semantic candidates collected via embedding search → the LLM confirms or denies each fuzzy pair → confirmed merges fold summaries/attributes into the canonical node → summaries then refresh in *flights* (bounded batches, one prompt per flight, group_id from the first node).
**Invariant:** fuzzy similarity alone never merges — the LLM confirms; summary updates are batched into flights rather than per-node calls; all nodes in a flight share a group_id; docstring few-shot examples never leak into summary prompts.
**Probe:** `tests/` node tests (exact collapse; LLM denial prevents merge; flight batching produces one call per N nodes; attribute extraction fills typed fields).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "resolve_extracted_nodes _resolve_with_llm _process_summary_flight extract_entity_summaries_batch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt LLM-confirmed resolution over fuzzy candidates and flight-batched summarization (one prompt per bounded batch); adapt flight size, thresholds, and context shape to host.
