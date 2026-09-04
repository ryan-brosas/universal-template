<!-- capsule-v2 -->
# Embedding field dispatch workflow — one config-driven loop over (table, column, transform) triples with per-field vector stores

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory project `graphrag`. **Question:** How does a pipeline embed several logical fields (text units, entity descriptions, community reports) through ONE embedding model without hard-coding each?

## Key facts
**Path/Symbol:** `graphrag/index/workflows/generate_text_embeddings.py` (`EmbeddingFieldConfig` dataclass :38-49; `EMBEDDING_FIELDS` registry :52-69; `run_workflow` :72-98; `generate_text_embeddings` :101-162). Reused verbatim by update runs: `update_text_embeddings.py:17-19` imports and calls it against the OUTPUT provider after merges.
**Signature:** `generate_text_embeddings(config, table_provider, callbacks, model, tokenizer) -> None`; per-field: `embed_text(input_table, callbacks, model, tokenizer, embed_column, batch_size, batch_max_tokens, num_threads, vector_store, output_table)` (operations layer mined in streaming-embed-text).
**Data Shape:** `EMBEDDING_FIELDS: dict[str, EmbeddingFieldConfig]` — keys are config embedding names (`text_unit`, `entity_description`, `community_full_content` via `graphrag.config.embeddings` constants); each entry = {name, table_name, embed_column, row_transform?}. Entity descriptions need `transform_entity_row_for_embedding` to synthesize the `title_description` column; others embed raw columns.

### Decisive source
```python
# generate_text_embeddings.py :112-128 — three guards in order:
for field_name in embedded_fields:                # only CONFIG-SELECTED fields run
    field_config = EMBEDDING_FIELDS[field_name]
    if not await table_provider.has(field_config.table_name):
        logger.warning("Embedding %s is specified but source table '%s' "
                       "is not in storage. Skipping.", ...)   # missing source = SKIP not crash
        continue
    vector_store = create_vector_store(
        config.vector_store,
        config.vector_store.index_schema[field_config.name],  # per-field index name/schema
    )
    vector_store.connect()
```
Snapshots are optional side-writes: when `config.snapshots.embeddings`, an extra output table `embeddings.{field}` captures vectors via `AsyncExitStack` (:130-143) so all handles close even if embed_text raises.
**Flow:** build ONE embedding model (cache child namespaced by `embed_text.model_instance_name`) → iterate configured fields → skip-missing → connect per-field vector store → open transformed input + optional snapshot output → embed_text streams batches → log per-field count.
**Invariant:** the field set comes from config (`config.embed_text.names`), never from the registry — adding an embedding requires BOTH a registry entry AND config selection; missing SOURCE tables warn-and-skip but a MISSING index_schema key raises KeyError (schema must cover every selectable field); update runs re-embed from the merged output tables, not deltas.
**Probe:** no dedicated unit test at this HEAD for generate_text_embeddings itself — operations-level streaming pinned by `tests/unit/indexing/operations/embed_text/test_embed_text.py` (mined in streaming-embed-text); verbs-level `tests/verbs/test_update_text_embeddings.py` exercises the reuse path; coverage caveat recorded here.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "graphrag", query: "EMBEDDING_FIELDS EmbeddingFieldConfig generate_text_embeddings row_transform", limit: 10 })`

## Verdict
Adopt the declarative (table, column, transform) registry driven by a config-selected subset with skip-on-missing-source; adapt store backends. Keep per-field vector-store naming — collapsing to one index breaks multi-field retrieval.
