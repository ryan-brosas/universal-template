<!-- capsule-v2 -->
# embed_text streaming pipeline — flush buffer of batch_size×num_threads; snippet-split oversized inputs and mean+L2-reconstitute; None embeddings are skipped rows, not errors

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how does embedding generation stream a whole table into a vector store with bounded API concurrency, token-budgeted batches, and graceful None handling?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/embed_text/embed_text.py`: `embed_text` (:23-90), `_flush_embedding_buffer` (:93-153); `run_embed_text.py`: `run_embed_text` (:185-226), `_execute` (:229-245), `_create_text_batches` (:248-277), `_prepare_embed_texts` (:280-301), `_reconstitute_embeddings` (:304-323).
**Signature:** `embed_text(input_table: Table, callbacks, model: LLMEmbedding, tokenizer, embed_column, batch_size, batch_max_tokens, num_threads, vector_store, id_column="id", output_table: Table | None = None) -> int`; returns total rows streamed.
**Data Shape:** result embeddings list is index-aligned with input texts; multi-snippet inputs collapse to ONE averaged vector; zero-snippet (empty) texts map to `None`.

### Decisive source
```python
flush_size = batch_size * num_threads        # each flush saturates concurrency
...
texts, input_sizes = _prepare_embed_texts(input, tokenizer, batch_max_tokens)  # split >8191-token inputs (overlap 100)
text_batches = _create_text_batches(texts, tokenizer, batch_size, batch_max_tokens)
# batch cut when EITHER limit hits:
if len(current_batch) >= max_batch_size or current_batch_tokens + token_count > max_batch_tokens:
    ...
embeddings = _reconstitute_embeddings(embeddings, input_sizes)
# per original text: size 0 → None | size 1 → as-is | size n → L2-normalized mean of its snippets' vectors
for doc_id, doc_vector in zip(ids, vectors, strict=True):
    if doc_vector is None: skipped += 1; continue      # skip-and-warn, never raise
    documents.append(VectorStoreDocument(id=doc_id, vector=doc_vector))
vector_store.load_documents(documents)
```

**Flow:** `create_index()` first → stream rows (missing embed-column text becomes `""`, never skipped) → buffer until `batch_size × num_threads` → flush through `run_embed_text` (semaphore-bounded concurrent batch calls) → load non-None docs into the vector store AND optionally mirror `{id, embedding}` rows to an output table → final partial flush after the stream ends.
**Invariant:** (1) Buffer sizing guarantees every flush has enough work to keep all `num_threads` batches in flight. (2) Batches respect BOTH count and token ceilings (Azure-style 16×8191 limits baked in). (3) A failed/empty embedding is a MISSING vector for that id — the id simply doesn't enter the store; the run continues. (4) Reconstitution preserves input order strictly by cursor arithmetic over `sizes`.
**Probe:** `tests/unit/indexing/operations/embed_text/test_embed_text.py`: basic round-trip :106-148, two-flush batching `mock_run.call_count == 2` :152-187, pretransformed rows :191-232, empty-string fill `test_embed_text_none_values_filled` :236-265, numpy→list coercion :326-373, partial-None skip :377-412.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "embed_text run_embed_text _create_text_batches _reconstitute_embeddings flush_embedding_buffer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt streaming-buffered embedding with dual-limit batching, snippet-split + normalized-mean reconstitution, and skip-not-fail None handling; adapt chunk sizes to the host embedding model's real limits; keep `strict=True` zips — they are what makes cursor drift impossible.
