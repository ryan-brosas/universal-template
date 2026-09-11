<!-- capsule-v2 -->
|# Ollama future-proof stub — how do you keep a provider working automatically against an unbuilt upstream feature?

## supports_multimodal=False gates dispatch TODAY; embed_images still speaks the PROPOSED upstream schema so support lands without a code change
**Path/Symbol:** `backend/python/app/services/embeddings/multimodal/ollama_provider.py` (whole file L1–88): docstring :1–18 (open feature requests ollama/ollama#5304 #16076), `supports_multimodal -> False` :45–46, best-effort `/api/embed` POST with proposed `images:[...]` field :52–83, default base_url fallback :31/:41.
**Signature:** `def supports_multimodal(self) -> bool` (the ONLY overriding provider); `async embed_images(image_base64s) -> list[ImageEmbeddingResult]`.
**Data Shape:** request `{"model": ..., "images": [image_base64]}` to `{base_url}/api/embed` (timeout 60s, Semaphore(5)); response `data.get("embeddings") or []` — empty ⇒ descriptive error naming the likely cause.

### Decisive source
```python
def supports_multimodal(self) -> bool:
    return False   # callers don't silently store broken/absent vectors

async def embed_single(...):
    resp = await client.post(f"{self.base_url}/api/embed",
                             json={"model": self.model_name, "images": [image_base64]})
    ...
    if not embeddings:
        return ImageEmbeddingResult(
            index=i,
            error=("Ollama did not return an embedding for the image — "
                   "this Ollama build likely doesn't support native "
                   "multimodal embedding yet."))
```

**Flow:** `VectorStore._process_image_embeddings` checks `provider.supports_multimodal()` AFTER factory create → Ollama returns False ⇒ caller logs "Unsupported embedding provider for images" and returns [] (VLM-description fallback remains the product path). If dispatched anyway (direct use/future gate removal), every image yields either an embedding (fork/build shipped support) or a self-describing error.
**Invariant:** the capability flag is the CONTRACT for callers; the wire schema inside `embed_images` is a BET on the upstream proposal (`images:` alongside `input`). Keeping the two separate lets upstream support flip the flag once instead of rewriting the provider.
**Probe:** deterministic pins (no dedicated suite at this pin — coverage caveat): `grep -c 'return False' backend/python/app/services/embeddings/multimodal/ollama_provider.py` == 1; `grep -cF '"images": [image_base64]' backend/python/app/services/embeddings/multimodal/ollama_provider.py` == 1; consumer gate `grep -c 'provider.supports_multimodal()' backend/python/app/modules/transformers/vectorstore.py` ≥ 1 (:817).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "OllamaMultimodalProvider supports_multimodal api/embed images", limit: 10 });
```

## Verdict
Adopt capability-flag gating plus forward-compatible wire-schema betting for not-yet-shipped upstream features; adapt the endpoint/schema to whatever upstream lands; omit nothing — small file, fully portable. Coverage caveat: pinned by deterministic greps + the consumer-side gate; no direct upstream spec at `c28d133`.
