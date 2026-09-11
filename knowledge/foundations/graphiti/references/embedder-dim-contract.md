<!-- capsule-v2 -->
# Embedder dim contract — three slicing strategies behind one frozen config

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** where should the configured embedding dimensionality be enforced — API-side, slice-side, or not at all — when different providers offer different mechanisms?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/embedder/client.py:EMBEDDING_DIM` (:24, env `EMBEDDING_DIM` default 1024), `EmbedderConfig.embedding_dim` (frozen Field :27), `EmbedderClient.create/create_batch` (:32/:37, batch raises NotImplementedError by default); providers `openai.py` (:55–66), `voyage.py` (:52–75), `azure_openai.py` (:28–71), `gemini.py` (:88–183).
**Signature:** `create(input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]) -> list[float]`; `EmbedderConfig(embedding_dim=FROZEN)`.
**Data Shape:** single-create returns ONE vector even for list inputs (callers rely on this for name/name_embedding fields); create_batch returns one vector per input; dim comes from a module-level env read at IMPORT time.

### Decisive source
```python
# openai.py / voyage.py — TRUNCATE client-side:
return result.data[0].embedding[: self.config.embedding_dim]
return [float(x) for x in result.embeddings[0][: self.config.embedding_dim]]

# gemini.py — request the dim from the API:
config=types.EmbedContentConfig(output_dimensionality=self.config.embedding_dim)
return result.embeddings[0].values            # trust the API's shape

# azure_openai.py — PASSTHROUGH, no slicing anywhere:
return response.data[0].embedding             # whatever the deployment returns
```

**Flow:** OpenAI text-embedding-3-* supports `dimensions` server-side but graphiti instead slices the returned vector; Voyage returns fixed-dim vectors that get sliced; Gemini passes `output_dimensionality`; Azure delegates dimension choice entirely to the deployment config.
**Invariant:** (1) mixing strategies is safe ONLY because downstream consumers index positionally into vectors of length `embedding_dim` — a porter adding a provider must pick one strategy and keep lengths consistent or FalkorDB `vecf32()` casts will misalign; (2) `create()` must return exactly one vector for ANY accepted input shape (single-string callers would break on a list); (3) `embedding_dim` is frozen post-init because stored vectors can't be re-dimensioned without a rebuild; (4) Gemini batches at 100 but forces batch_size=1 for `gemini-embedding-001`, falling back to per-item embedding when a batch call fails — partial-failure isolation over throughput.
**Probe:** `tests/embedder/test_openai.py`, `test_voyage.py`, `test_gemini.py` (provider contracts incl. slicing/batching via fixtures in `embedder_fixtures.py`); azure has NO direct test file (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "EmbedderConfig embedding_dim create_batch VoyageAIEmbedder GeminiEmbedder", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the frozen-config + single-vector-from-any-shape contract; choose ONE slicing strategy per provider deliberately (slice when the API can't be trusted, request-when-supported); omit per-item fallback if your provider batches atomically.
