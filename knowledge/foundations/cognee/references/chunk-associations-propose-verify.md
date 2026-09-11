<!-- capsule-v2 -->
# Chunk associations — vector candidates + LLM verdicts with pair dedup

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do you link semantically related chunks with weighted graph edges without comparing the same pair twice or trusting raw vector similarity?

## create_chunk_associations
**Path/Symbol:** `cognee/tasks/chunks/create_chunk_associations.py:create_chunk_associations` (:101-231), `_compare_chunks` (:36-71), `_create_edge` (:74-98).
**Signature:** `async create_chunk_associations(chunks, similarity_threshold=0.7, min_chunk_length=10, top_k_candidates=None, ...) -> AsyncGenerator[str]` (async GENERATOR: yields each input chunk unchanged so it composes mid-pipeline).
**Data Shape:** Edge `(chunk_1_id, chunk_2_id, "associated_with", {weight, association_type, reasoning, ontology_valid: False})`; LLM verdict model `ChunkSimilarity{are_similar, similarity_score 0-1, reasoning, association_type?}`.

### Decisive source
```python
# id resolution: the TEXT is searched against DocumentChunk_text limit=1 to recover
# the persisted chunk id — text alone has no identity in the graph:
results = await vector_engine.search("DocumentChunk_text", chunk_text, limit=1)
id_to_text[str(results[0].id)] = chunk_text

for candidate in candidates:
    candidate_id = str(candidate.id)
    if candidate_id == chunk_id or candidate_id not in id_to_text: continue
    pair_key = tuple(sorted([chunk_id, candidate_id]))   # undirected dedup
    if pair_key in compared_pairs: continue
    compared_pairs.add(pair_key)
...
provenance_kwargs = await graph_provenance_write_kwargs(
    graph_engine, ctx,
    fallback_data_id=uuid5(NAMESPACE_URL, "cognee:chunk-associations"))
```

**Flow:** filter short/non-string chunks (<2 valid ⇒ pass-through) → resolve ids via per-chunk self-search → per chunk vector search (limit = `top_k_candidates + 1`, self excluded) → LLM verdict per unseen pair (LLM failure ⇒ are_similar=False fallback score 0.0 — association creation degrades, never raises) → threshold gate (`are_similar AND score ≥ threshold`) → persist all edges + re-index edge texts; persistence failure RE-RAISES.
**Invariant:** (1) Sorted-pair key is what bounds cost at n·k comparisons with zero repeats. (2) Asymmetric error policy by stage: LLM/lookup failures degrade silently; graph persistence failures propagate. (3) Provenance needs a data_id even when the caller passed none — deterministic namespace-URL uuid5 fallback keeps attribution total. (4) Vector similarity only PROPOSES candidates; the LLM score gates the write.
**Probe:** `cognee/tests/test_chunk_associations.py::test_chunk_associations_configurable_parameters` (requires LLM_API_KEY — env-gated); provenance unit pins in `cognee/tests/unit/tasks/chunks/test_create_chunk_associations_provenance.py`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "create_chunk_associations compared_pairs associated_with ChunkSimilarity", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-stage propose-then-verify association with sorted-pair dedup and a deterministic provenance fallback id; adapt thresholds and verdict schema; skip entirely if you don't want LLM-priced link discovery.
