<!-- capsule-v2 -->
|# Voyage delegation + short-batch tail completion — how do you wrap an already-multimodal LangChain Embeddings instance under the result-object contract?

## Read batch_size off the delegate; complete the tail with errors when the response is short; batch failure ⇒ error per member
**Path/Symbol:** `backend/python/app/services/embeddings/multimodal/voyage_provider.py` (whole file L1–72): `_DEFAULT_BATCH_SIZE=7` :20, `embed_images` :34–62, short-response tail fill :42–55, exception path :56–62.
**Signature:** `VoyageMultimodalProvider(dense_embeddings: Embeddings, logger=None)`; `async embed_images(image_base64s) -> list[ImageEmbeddingResult]`; batch size resolved via `getattr(self.dense_embeddings, "batch_size", _DEFAULT_BATCH_SIZE)`.
**Data Shape:** delegates raw base64 image strings to `dense_embeddings.aembed_documents(batch_imgs)` — the LangChain instance (`app.utils.custom_embeddings.VoyageEmbeddings`) owns the multimodal part-shaping; provider owns batching/concurrency (Semaphore(5)) and result accounting only.

### Decisive source
```python
# A short response must not silently drop its tail --
# every input index owes the caller a result.
results = [ImageEmbeddingResult(index=batch_start + i, embedding=list(e))
           for i, e in enumerate(embeddings)]
results.extend(
    ImageEmbeddingResult(index=batch_start + i,
                         error="no embedding returned for this image")
    for i in range(len(embeddings), len(batch_imgs)))
```

**Flow:** slice inputs by delegate's batch_size → per batch call `aembed_documents` → zip embeddings positionally (LangChain guarantees order alignment) → EXTEND with error results for any tail the response didn't cover → on whole-batch exception, one error per member. No normalisation step here: the delegate consumes base64 directly.
**Invariant:** positional zip over LangChain's ordered return is safe ONLY because the tail-completion loop guarantees length parity; skipping it turns a truncated provider response into silently missing vectors (the exact class of bug `_response.map_embedding_response` guards against for index-keyed APIs).
**Probe:** deterministic pins (no dedicated suite at this pin — coverage caveat): `grep -c 'for i in range(len(embeddings), len(batch_imgs))' backend/python/app/services/embeddings/multimodal/voyage_provider.py` == 1; `grep -c 'getattr(self.dense_embeddings, "batch_size"' <same>` == 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "VoyageMultimodalProvider aembed_documents dense_embeddings", limit: 10 });
```

## Verdict
Adopt delegation-plus-accounting split (delegate owns wire format, wrapper owns batching/result contract) and the tail-completion invariant; adapt the delegate hook (`aembed_documents`) to your embedding facade; omit Voyage specifics if unused. Coverage caveat: pinned by deterministic greps + the shared never-drop contract tested through the Jina suite.
