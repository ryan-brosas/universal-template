<!-- capsule-v2 -->
# VertexAI embed_batch chunking — 250-batch loop with count-mismatch tripwire

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how does a native-batch embedder override guarantee it never silently returns fewer vectors than inputs?

## Connected graph-selected seam
**Path/Symbol:** `mem0/embeddings/vertexai.py`: `VertexAIEmbedding.embed_batch` (:81-101); empty-guard at :82.
**Signature:** `embed_batch(self, texts, memory_action="add") -> List[List[float]]`.
**Data Shape:** in: list of texts + action; out: exactly one embedding vector per input text (verified by explicit length assert).

### Decisive source
```python
if not texts:
    return []
...
for i in range(0, len(texts), 250):
    chunk = texts[i : i + 250]
    inputs = [TextEmbeddingInput(text=t, task_type=embedding_type) for t in chunk]
    results = self.model.get_embeddings(texts=inputs, output_dimensionality=self.config.embedding_dims)
    all_embeddings.extend(r.values for r in results)
if len(all_embeddings) != len(texts):
    raise ValueError(
        f"Vertex AI embed_batch() returned {len(all_embeddings)} embeddings for {len(texts)} texts"
        f" using model '{self.config.model}'"
    )
```

**Flow:** falsy-in ⇒ empty-out (no API call) → task-type resolved ONCE for the whole batch → fixed 250-item chunks through the native API (the provider's documented max) → extend flat vector list → hard equality check before returning.
**Invariant:** the count-mismatch raise is the porting essence — a ragged or short result from a partial API failure must become a LOUD error, never a positional zip corruption downstream (callers pair texts↔vectors by index). A naive port that drops the check turns any silent truncation into memories embedded against the wrong text. Note also that the task-type map is consulted once per batch call, not per item, and unknown `memory_action` values raise before any network spend.
**Probe:** `grep -cF 'for i in range(0, len(texts), 250):' mem0/embeddings/vertexai.py` (=1); `grep -cF 'if len(all_embeddings) != len(texts):' mem0/embeddings/vertexai.py` (=1).
**Probe (direct test):** `tests/embeddings/test_vertexai_embeddings.py::test_embed_batch_single_call` (:165), `::test_embed_batch_empty_list` (:186), `::test_embed_batch_count_mismatch_raises` (:200), and `::test_embed_batch_chunking_triggers_two_api_calls` (:263, "300 texts must produce exactly 2 get_embeddings calls") pin the whole contract via mocked `TextEmbeddingModel`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "embed_batch get_embeddings output_dimensionality", limit: 10 });
```

## Verdict
Adopt chunk-loop + final count assertion as the canonical shape for every native-batch override; adapt chunk size to your provider's max; omit the guard and you inherit a silent data-corruption class.
