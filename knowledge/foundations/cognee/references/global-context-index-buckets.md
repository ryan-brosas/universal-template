<!-- capsule-v2 -->
# Global context index — bucketed placement for cross-dataset memory

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do you give every retrieval a compact global-context prelude without scanning the whole graph per query?

## Global context index build/update + retrieval-side consumption
**Path/Symbol:** `cognee/tasks/memify/global_context_index/build.py` (:1-276), `update.py` (:1-321), `cognee/tasks/memify/global_context_index/bucketing/graph/placement.py` (:1-549) + `bucketing/vector/placement.py` (:1-236); inputs `cognee/modules/graph/methods/get_global_context_graph_inputs.py:get_global_context_graph_inputs` (:1-402); consumers `cognee/modules/retrieval/utils/global_context.py:search_top_global_context_summaries`, `format_global_context_prelude`; retriever hooks (`include_global_context_index`, `global_context_index_top_k=3`) in graph_completion_retriever.py :66-67/:273-292 and hybrid_retriever.py :69-70/:206-224.
**Signature:** memify build/update tasks place summary DataPoints into buckets; retrieval searches a dedicated summaries collection and prepends a formatted prelude to the graph context.
**Data Shape:** Prelude = `format_global_context_prelude(root_text, top_summaries)`; hybrid labels it `## Global context`.

### Decisive source
```python
# retrieval side (graph_completion_retriever.get_context_from_objects):
prelude = await self._build_global_context_prelude(query)
if not prelude and not graph_context: return ""
if not prelude: return graph_context
if not graph_context: return prelude
return f"{prelude}\n\n{graph_context}"     # global prelude FIRST, then triplets
```

**Flow:** memify pipelines consolidate entities → bucket placement assigns each consolidated summary a bucket in the graph and mirrors it into the vector index (two placement strategies: graph-shaped and vector-shaped) → update path refreshes buckets incrementally instead of full rebuilds → search time queries only the top-k bucket summaries + root text.
**Invariant:** (1) The prelude is additive context, never a REPLACEMENT — when both exist they concatenate with global first; either alone still renders. (2) Opt-in on both retrievers (`include_global_context_index=False` default ⇒ zero extra reads). (3) Incremental updates must keep graph-bucket and vector-row placement consistent or the two indexes disagree about what "global" says.
**Probe:** `cognee/tests/unit/modules/graph/test_global_context_graph_inputs.py`; `cognee/tests/unit/modules/retrieval/test_global_context.py`; memify pipeline tests under `cognee/tests/unit/memify_pipelines/`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "global_context_index placement bucket build update summaries", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt opt-in bucketed global summaries + prelude concatenation order; adapt bucketing strategy to your scale; omit if your corpus is small enough for direct search.
