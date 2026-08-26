<!-- capsule-v2 -->
# OpenAI embeddings batch — when do you pass `dimensions`, how do you chunk native batch calls, and why must results be re-sorted by index?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** what does a porter need to keep so embedding batches stay correct against both OpenAI and OpenAI-compatible (vLLM/Voyage) backends?

## Connected graph-selected seam
**Path/Symbol:** `mem0/embeddings/openai.py`: ctor dimension gate (:15-19), `_pass_dimensions_to_api` (:18) consumed at :53-54 and :72-73, newline scrub (:47, :63), `embed_batch` MAX_BATCH=100 chunk loop (:57-81) with index re-sort + count assertion (:75-80); base contract `mem0/embeddings/base.py` `embed_batch` sequential default (:33-47). Direct tests `tests/embeddings/test_openai_embeddings.py`.
**Signature:** `embed(text, memory_action=None) -> list[float]`; `embed_batch(texts: list[str], memory_action="add") -> list[list[float]]`.
**Data Shape:** single text in → vector out; batch → list of vectors ORDERED to match input; `embedding_dims=None` means "user never set it" and defaults the stored dims to 1536 WITHOUT forwarding a `dimensions` param.

### Decisive source
```python
# Only pass `dimensions` to the API when the user set embedding_dims; non-matryoshka
# OpenAI-compatible backends (vLLM, Voyage, etc.) reject the parameter
self._pass_dimensions_to_api = self.config.embedding_dims is not None
self.config.embedding_dims = self.config.embedding_dims or 1536

MAX_BATCH = 100
for i in range(0, len(texts), MAX_BATCH):
    chunk = texts[i:i+MAX_BATCH]
    response = self.client.embeddings.create(**kwargs)
    all_embeddings.extend(item.embedding for item in sorted(response.data, key=lambda x: x.index))
if len(all_embeddings) != len(texts):
    raise ValueError(f"OpenAI embed_batch() returned {len(all_embeddings)} "
                     f"embeddings for {len(texts)} texts using model '{self.config.model}'")
```

**Flow:** every text is newline-scrubbed (`\n`→space, OpenAI's own recommendation) → kwargs carry input/model/encoding_format="float" plus `dimensions` ONLY under the user-set gate → batch path chunks at 100 (API limit), extends from response.data RE-SORTED by `.index` because providers may return rows out of order → final count mismatch raises loudly instead of returning a silently misaligned list.
**Invariant:** (1) `dimensions` is opt-in at the API boundary — sending it unconditionally breaks non-matryoshka compatible backends while omitting it breaks users who asked for 512-dim truncation; (2) sort-by-index before extend — trusting response order corrupts text↔vector pairing with NO error; (3) count-equality assert converts provider truncation into a loud failure; (4) base-class default `embed_batch` loops `embed()` one-by-one — only subclasses with native batch APIs override (performance contract, not correctness).
**Probe:** `tests/embeddings/test_openai_embeddings.py` (mocked client asserts call kwargs incl. conditional dimensions and batch ordering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "embed_batch OpenAIEmbedding _pass_dimensions_to_api", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dimensions-gate, index re-sort, and count assert verbatim — each kills a silent-corruption mode; adapt MAX_BATCH to your provider's documented limit; omit per-provider embedder twins (azure/gemini/ollama/…) unless you serve them — they repeat this same contract shape.
