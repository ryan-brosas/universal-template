<!-- capsule-v2 -->
# Capability-seam monorepo split + named-model config — how do you cut a RAG pipeline into swappable packages without entangling providers?

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag` (full mode, 5,367 nodes / 24,019 edges, generation 2026-08-16). **Question:** how does the 2025 monorepo split isolate provider/backends behind interfaces so pipeline code never touches a vendor, and what does the config object look that wires it?

## The seven-package seam graph
**Path/Symbol:** `packages/{graphrag,graphrag-llm,graphrag-storage,graphrag-vectors,graphrag-cache,graphrag-chunking,graphrag-input}` (+ `graphrag-common` Factory helper). Core `graphrag` imports only the *interfaces*: `LLMCompletion`/`LLMEmbedding`/`Tokenizer` from llm, `Storage`/table ABCs from storage, `VectorStore` from vectors, `Cache` ABC from cache.
**Signature:** each side-package ships an ABC + `{x}_factory.py` (`cache_factory.py`, `storage_factory.py`, llm/vector equivalents) selected by a config enum; core receives constructed objects via constructor injection (see search capsules).
**Data Shape:** every pipeline stage persists behind insert/upsert/read contracts (documents, text units, entities, relationships, community reports) as Parquet tables written to `output/`; deterministic integer/uuid ids make any step resumable.

### Decisive source
```python
# packages/graphrag/graphrag/config/models/graph_rag_config.py:51-59,277-299
class GraphRagConfig(BaseModel):
    completion_models: dict[str, ModelConfig]   # NAMED registry, not one model
    embedding_models: dict[str, ModelConfig]
    ...
    def get_completion_model_config(self, model_id: str) -> ModelConfig:
        if model_id not in self.completion_models:
            err_msg = f"Model ID {model_id} not found in completion_models..."
            raise ValueError(err_msg)
        return self.completion_models[model_id]
```
Per-feature sections (`local_search`, `global_search`, `drift_search`, `basic_search`,
`extract_graph`, … :233-251) each name WHICH registry entry they use, so indexing
can run tiny local models while queries use cloud models — no pipeline change.

**Flow:** `settings.yaml` → `GraphRAGConfig` validation (`@model_validator mode="after"` :325-333 resolves+absolutizes input/output/reporting base dirs, auto-injects one `IndexSchema` per known embedding into `vector_store.index_schema` :253-267) → factories build backend objects → workflows/index operations (`index/operations/`: extract, summarize→community reports, cluster via modularity, covariates; each with strategy subpackages) write stage tables → query modes load those tables through the same ABCs. `prompt_tune/` generates dataset-specific extraction prompts into settings.
**Invariant:** core depends on abstractions only — swapping Parquet↔blob↔memory storage, json↔memory↔noop cache (`noop` makes CI cheap), or any model provider is a CONFIG change; cache persistence makes indexing *replayable* (hits skip re-extraction).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "GraphRagConfig get_completion_model_config factory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the seams-first package cut (llm/storage/vectors/cache/chunking/input), the named-model registry with per-feature model selection, and persisted-stage ids for resume/replay; adapt package boundaries, backend lists, and defaults to host scale; omit Azure-specific bindings (`azure_blob_storage`, `azure_cosmos_storage`) and the unified-search-app unless a target needs them. Coverage caveat: config schemas smoke/integration-tested only (`tests/unit/config/` covers per-section models; no unit test pins `get_completion_model_config`'s error path).
