<!-- capsule-v2 -->
# Unified engine boundary — capability-gated graph+vector writes

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does one storage call site serve backends that write graph and vector together vs separately, without if-elif ladders leaking into business logic?

## get_unified_engine + EngineCapability
**Path/Symbol:** `cognee/infrastructure/databases/unified/` (`get_unified_engine`, `capabilities.EngineCapability` — imported at `add_data_points.py:6-7`); usage `add_data_points.py` (:111-114, :183-212); retriever consumption `graph_completion_retriever.py:130-131` (`unified_engine.graph.is_empty()`), hybrid `_retrieve_one` (:104, `vector.embedding_engine.embed_text`).
**Signature:** `unified = await get_unified_engine(); unified.graph / unified.vector / unified.has_capability(EngineCapability.HYBRID_WRITE)`.
**Data Shape:** Capability flags decide the write shape; every backend answers the same interface questions.

### Decisive source
```python
unified = await get_unified_engine()
graph_engine = unified.graph
vector_engine = unified.vector
use_hybrid = unified.has_capability(EngineCapability.HYBRID_WRITE)

if use_hybrid:
    await graph_engine.add_nodes_with_vectors(nodes)      # one atomic dual write
elif graph_only:
    await graph_engine.add_nodes(nodes)                    # no vector engine at all
else:
    await asyncio.gather(                                  # split engines: parallel
        graph_engine.add_nodes(nodes),
        index_data_points([node.model_copy(deep=True) for node in nodes],
                          vector_engine=vector_engine))
```

**Flow:** capability check once per batch → three write shapes (hybrid atomic / graph-only / split-parallel with defensive deep copies handed to the indexer) → provenance folding availability keyed off the same capability split (fold on non-hybrid; attach-pass on hybrid).
**Invariant:** (1) The capability query replaces provider-name string matching everywhere downstream — a new backend declares capabilities instead of editing call sites. (2) Split-engine indexing gets `model_copy(deep=True)` because the vector indexer serializes while graph adapters may mutate properties. (3) Retrieval-side code also goes through the pair (`unified_engine.graph.is_empty()`) so empty-graph checks are consistent across engines.
**Probe:** `cognee/tests/unit/infrastructure/databases/test_unified_store_engine.py`; capability wiring visible in `cognee/tests/unit/infrastructure/databases/test_neptune_analytics_hybrid.py`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "get_unified_engine EngineCapability HYBRID_WRITE add_nodes_with_vectors", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capability-flag dispatch over provider branching and deep-copy at the engine hand-off; adapt capability names to your stores; omit graph_only unless you have extraction-only pipelines.
