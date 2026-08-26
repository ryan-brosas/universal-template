<!-- capsule-v2 -->
# DLT deterministic route — LLM-free pipeline for structured sources

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do you ingest relational/structured data into a knowledge graph WITHOUT paying for or risking LLM extraction?

## get_dlt_tasks
**Path/Symbol:** `cognee/api/v1/cognify/cognify.py:get_dlt_tasks` (:433-476); route entry via `CognifyRoute.DLT_SOURCE` (routing.py :32-36).
**Signature:** `async get_dlt_tasks(chunk_size=None, chunks_per_batch=None) -> list[Task]` (default batch 100, not the standard 2000).
**Data Shape:** One DocumentChunk per manifest row; graph structure comes from the RELATIONAL SCHEMA (`extract_dlt_source_edges`) — FK edges are deterministic, not inferred.

### Decisive source
```python
return [
    Task(classify_documents),
    # PURGE: manifests have stable ids — drop the source's previously derived
    # artifacts so re-emission REPLACES instead of accreting:
    Task(purge_stale_dlt_source_artifacts),
    Task(extract_chunks_from_documents, max_chunk_size=..., chunker=TextChunker),
    Task(add_data_points, embed_triplets=cognify_config.triplet_embedding,
         task_config={"batch_size": chunks_per_batch}),
    # Cross-batch dedup state lives in ctx.extras (per data item = per source), so
    # these Task objects are safe to share across datasets:
    Task(extract_dlt_source_edges),
]
```

**Flow:** classify → purge stale derived artifacts (stable ids make replace-on-reingest correct) → chunk rows verbatim → store+index → schema-driven edges. Deliberate omissions vs `get_default_tasks`, documented in the docstring: contradiction detection (an LLM pass over deterministic rows) and functional_relationships (LLM-extracted temporal facts only).
**Invariant:** (1) Purge-before-insert REQUIRES stable ids — with random ids it would delete fresh data. (2) Shared Task objects are safe ONLY because per-source dedup state is keyed under ctx.extras per data item — a porter who moves that state onto the Task object breaks multi-dataset runs. (3) No LLM task ⇒ no contradiction/functional tasks; keeping them would silently reintroduce model cost and nondeterminism into a deterministic route.
**Probe:** `cognee/tests/unit/modules/cognify/test_cognify_single_logical_run.py::TestRouting.test_manifest_routes_to_dlt_source`; ingestion tests `cognee/tests/unit/modules/ingestion/`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "get_dlt_tasks extract_dlt_source_edges purge_stale_dlt_source_artifacts", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the id-stable purge-and-replace pattern and schema-derived edges for structured sources; adapt to your manifest format; omit if you have no deterministic sources.
