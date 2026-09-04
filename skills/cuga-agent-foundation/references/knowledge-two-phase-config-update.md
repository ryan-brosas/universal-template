<!-- capsule-v2 -->
# Prepare/commit knowledge update — why does validation load the model BEFORE mutation, and which of the four rebind branches applies on commit?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you apply an embedder/config change at runtime so a bad model name 400s cleanly instead of 500ing mid-mutation — and what exactly gets rebuilt vs kept in each change class?

## Two-phase: prepare (all external calls, no mutation) → commit (pure in-memory)
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:3729-3813` (`prepare_knowledge_update`), `:3815-3944` (`commit_knowledge_update`), dataclass `PreparedKnowledgeUpdate` `:802-815`, typed error `EmbeddingModelLoadError` `:770-781`.
**Signature:** `prepare_knowledge_update(knowledge_cfg: dict) -> PreparedKnowledgeUpdate` raising `ValueError/TypeError` (bad input) or `EmbeddingModelLoadError(provider, model, cause)` (model won't load); `commit_knowledge_update(prepared) -> dict[str, Any]` with keys `embedding_changed/chunking_changed/metric_changed/reindex_recommended/dim_changed/previous_dim/new_dim/docling_changed`.
**Data Shape:** Prepared carries `validated: KnowledgeConfig` + booleans + OPTIONAL `new_embeddings: Embeddings | None` + `new_embedding_dim: int | None`. Profile expansion first: `rag_profile` params merged UNDER explicit keys.

### Decisive source
```python
# engine.py:3774-3779 — eager construction in PREPARE, not commit
if embedding_changed:
    # Local providers (fastembed/huggingface) load the model eagerly here,
    # so a large model still downloading (e.g. multilingual-e5-large is
    # ~2.2GB with external ONNX weights), a bad model name, or an
    # unresolved key fails RIGHT HERE. Surface a typed, actionable error
    # instead of letting an opaque ONNX/HTTP error 500 the publish.
    try:
        new_embeddings = create_embeddings(validated)
```
Commit's four rebind branches are mutually exclusive and ordered:
1. **Provider/model changed** (`prepared.new_embeddings` truthy): swap `_default_embeddings`+dim; dim counts as changed ONLY if old AND new dims both set (None→new is first-time init, NOT a change); clear `_vector_stores` + `_record_managers` under `_vector_store_lock`.
2. **Same model, new device** (`use_gpu` flipped for fastembed/huggingface): rebuild embeddings (ORT/PyTorch sessions immutable ⇒ rebind backend) but KEEP vector stores — same weights, vectors still valid, no reindex.
3. **Credential/base-url/extra-params-only fix**: old client cached a rejected key; rebuild it so the fix lands without restart; clear caches; construction doesn't hit the network so a still-bad key surfaces later at embed time.
4. **Docling knobs changed** (`pdf_mode`/`layout_engine`/`use_gpu`): clear ONLY `_docling_converters` — else switching layout_engine at runtime silently returns the stale converter built against the old setting.
Plus two side-contracts: ANY apply nulls `_embedder_probe_cache` (a key fix must force a fresh health probe); rerank_enabled triggers non-blocking background model prefetch so the first search doesn't pay a ~1.1GB fetch.

**Flow:** prepare: expand rag_profile under explicit keys → `KnowledgeConfig.coerce_and_validate(base=current)` → diff provider/model/chunk/metric → if embedding changed, construct embeddings NOW (+ dim probe only when an existing dim exists, so a fresh engine never makes a pointless remote call that would fail on missing keys) → return prepared. Commit: snapshot olds → copy every `KnowledgeConfig` field EXCEPT `persist_dir` from validated onto live config → run the branch ladder → bump `_apply_generation` iff any of e/c/m changed (this is what arms the ingest supersede ladder).
**Invariant:** All fallible external work happens in prepare; commit is pure memory mutation and can be treated as atomic by callers. The generation bump belongs to commit's tail — after config fields moved — so any worker captured before it is stale by definition.
**Probe:** `tests/unit/test_knowledge_embedder_load_error.py:33` (bad local model ⇒ typed `EmbeddingModelLoadError` raised from prepare); `tests/unit/test_knowledge_reindex_in_progress_guard.py:70-119` (vector-affecting apply raises `ReindexInProgressError` naming the collection while reindex runs; search-side knobs still apply).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "prepare_knowledge_update commit_knowledge_update PreparedKnowledgeUpdate EmbeddingModelLoadError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate-and-preflight-before-mutation with a prepared payload carrying pre-built expensive objects, plus the ordered rebind ladder distinguishing model-change / device-change / credential-change / parser-knob-change. Adapt the field set to your config schema. Omit profile-expansion details if you have no profile concept.
