<!-- capsule-v2 -->
# Report context prep workflow — graph-context vs text-unit-context twins feeding one summarizer

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory project `graphrag`. **Question:** How do the two community-report variants (LLM graph reports vs fast text reports) share a summarizer yet build completely different local contexts?

## Key facts
**Path/Symbol:** `graphrag/index/workflows/create_community_reports.py` (`run_workflow` :41-89; `create_community_reports` :92-140; `_prep_nodes` :143-161, `_prep_edges` :164-180, `_prep_claims` :183-199) vs `create_community_reports_text.py:84-119`. Shared machinery: `explode_communities`, `summarize_communities`, `finalize_community_reports`, per-variant `build_level_context`/`build_local_context` imported from DIFFERENT packages (`...summarize_communities.graph_context.context_builder` vs `...text_unit_context.context_builder`).
**Signature:** both end in `finalize_community_reports(community_reports, communities)`; graph variant reads relationships+entities+communities(+covariates when claims enabled); text variant reads entities+communities+text_units and uses `prompts.text_prompt` instead of `prompts.graph_prompt`.
**Data Shape:** `_prep_*` fill missing descriptions with "No Description" then pack detail columns into ONE dict-record column each: NODE_DETAILS {short_id, title, description, node_degree}, EDGE_DETAILS {short_id, source, target, description, degree}, CLAIM_DETAILS {short_id, subject, type, status, description}.

### Decisive source
```python
# create_community_reports.py :107-138 — the twin split is exactly two lines:
nodes = explode_communities(communities, entities)
nodes = _prep_nodes(nodes); edges = _prep_edges(relationships)
local_contexts = build_local_context(nodes, edges, claims, tokenizer, callbacks, max_input_length)  # GRAPH ctx
...
community_reports = await summarize_communities(nodes, communities, local_contexts,
    build_level_context, callbacks, model=model, prompt=prompt, ...)   # SAME summarizer both variants
```
```python
# create_community_reports_text.py :100-102 — text twin swaps ONLY the context builder + prompt:
local_contexts = build_local_context(communities, text_units, nodes, tokenizer, max_input_length)
```
Claims gate mirrors covariates plumbing: only loaded when `config.extract_claims.enabled AND provider.has("covariates")`.
**Flow:** DataReader loads tables → explode communities to member entities → prep (fillna + record-column packing) → per-community local contexts (token-budgeted) → level-by-level bottom-up summarization (mined in community-report-pipeline) → finalize merges reports back onto community keys.
**Invariant:** the summarizer/concurrency/finalize chain is IDENTICAL — variants differ ONLY in context-builder package and prompt; "No Description" placeholder is semantic (empty strings would break token budgeting/rating downstream); claims are optional at TWO gates (config flag AND table existence).
**Probe:** no dedicated unit test for either workflow file at this HEAD; summarize_communities/finalize behavior pinned by operations-level tests under `tests/unit/indexing/operations/` and query-side report consumption (`tests/unit/query/`) — coverage caveat recorded here.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "graphrag", query: "build_local_context explode_communities summarize_communities finalize_community_reports", limit: 10 })`

## Verdict
Adopt the strategy-split: shared summarization kernel + swappable context builders selected per pipeline (standard=graph, fast=text). The record-column packing shape is what prompts expect — do not invent a second format.
