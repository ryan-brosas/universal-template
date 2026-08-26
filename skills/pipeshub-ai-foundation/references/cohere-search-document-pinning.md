<!-- capsule-v2 -->
|# Cohere search_document pinning — which input_type can legally carry an image through Cohere v4 `inputs`, and how do older models get flagged?

## input_type MUST be "search_document" (not "image"); batch-via-inputs is v4-only; older models warn at construction
**Path/Symbol:** `backend/python/app/services/embeddings/multimodal/cohere_provider.py` (whole file L1–104): module docstring :1–16 (the WHY), `_IMAGE_INPUT_TYPE="search_document"` :31, `supports_inputs_image_batch` :34–37, `cohere_image_input_type` :40–46 (retains model_name for future generations), constructor warning :55–60, executor-offloaded sync client :72–100.
**Signature:** `cohere_image_input_type(model_name: str | None) -> str` (constant-returning); `supports_inputs_image_batch(model_name) -> bool` (`"v4" or "embed-4" in lower(name)`); `CohereMultimodalProvider(api_key, model_name, logger=None)`.
**Data Shape:** `inputs=[{"content": [{"type": "image_url", "image_url": {"url": <base64-or-uri>}}]}]`, `input_type="search_document"`, `embedding_types=["float"]`; sync `ClientV2.embed` wrapped in `loop.run_in_executor(None, ...)` under Semaphore(10).

### Decisive source
```python
# Cohere documents that `inputs` accepts only search_query/search_document/
# classification/clustering as input_type -- "image" is EXCLUDED from that set,
# even though it remains valid for the older `images` parameter. On embed-v4.0
# "image" silently falls back to search_document and Cohere recommends passing
# search_document directly. Batch image embedding via `inputs` is an
# embed-v4.0 feature (up to 96 inputs); embed-v3.0 needs the separate
# `images` parameter, one image per call.
_IMAGE_INPUT_TYPE = "search_document"
if logger and not supports_inputs_image_batch(model_name):
    logger.warning("Cohere model %r predates embed-v4.0; ... requests may be rejected.", ...)
```

**Flow:** construction validates generation (v3 ⇒ warning, proceed) → per-image single-item `inputs` batches through the executor → oversized-image failures are logged as expected SKIPS ("image size must be at most"), all other failures logged as real errors — neither disappears into the result object unlogged.
**Invariant:** sending `input_type="image"` through `inputs` relies on undocumented silent fallback; the constant exists so the reason survives next to the code that needs it. Per-image concurrency cap 10; every index still gets exactly one result.
**Probe:** deterministic pins (no dedicated suite at this pin — coverage caveat): `grep -cF '_IMAGE_INPUT_TYPE = "search_document"' backend/python/app/services/embeddings/multimodal/cohere_provider.py` == 1; `grep -c 'predates embed-v4.0' <same>` == 1; `grep -c 'image size must be at most' <same>` == 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "CohereMultimodalProvider search_document inputs input_type", limit: 10 });
```

## Verdict
Adopt the documented-input_type discipline (never rely on undocumented enum fallbacks) and the v4-generation gate-with-warning; adapt API params to your Cohere SDK generation; omit the executor shim if your client is natively async. Coverage caveat: pinned by deterministic greps; no direct upstream spec for this class at `c28d133`.
