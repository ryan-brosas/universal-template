<!-- capsule-v2 -->
|# Titan HTTP-200 failure channel — how do you read per-image failures out of a Bedrock response that returns 200 even when embedding failed?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** How does the Bedrock/Titan multimodal provider detect failures when the transport layer reports success, and how is the output dimension chosen?

## body["message"] non-empty ⇒ failure despite HTTP 200; outputEmbeddingLength must be one of {256,384,1024}
**Path/Symbol:** `backend/python/app/services/embeddings/multimodal/bedrock_provider.py` (whole file L1–149): `_SUPPORTED_OUTPUT_EMBEDDING_LENGTHS=(256,384,1024)` :25, `_resolve_output_length` :48–64, client build :74–86 (`NoCredentialsError` → typed `EmbeddingError`), `embed_images` :70–149 with `return_exceptions=True` normalisation loop :137–149.
**Signature:** `async embed_images(self, image_base64s: list[str]) -> list[ImageEmbeddingResult]`; static `_resolve_output_length(embedding_size: int | None, logger) -> int`.
**Data Shape:** request body `{"inputImage": <base64>, "embeddingConfig": {"outputEmbeddingLength": int}}`; response `body["message"]` (failure text, present ONLY on failure) / `body["embedding"]` (list[float]). boto3 sync calls wrapped via `loop.run_in_executor(None, ...)` under a Semaphore(10).

### Decisive source
```python
# Titan reports per-image generation failures in `message`
# while still returning HTTP 200, so a missing/!=None message is the only
# signal that `embedding` is real.
failure = body.get("message")
if failure:
    ...
    return ImageEmbeddingResult(index=i, error=str(failure))
embedding = body.get("embedding")
if not embedding:
    return ImageEmbeddingResult(index=i, error="no embedding returned for this image")

raw_results = await asyncio.gather(..., return_exceptions=True)
for i, r in enumerate(raw_results):
    if isinstance(r, ImageEmbeddingResult): results.append(r)
    else:
        logger.warning(...)   # bare exception => normalised into a result,
        results.append(ImageEmbeddingResult(index=i, error=str(r)))  # batch survives
```

**Flow:** resolve output length at construction (collection dim ∈ {256,384,1024} honoured, anything else warns and falls back to 1024 with an explicit "image points will be dropped as dimension mismatches" message) → per-image invoke → check `message` BEFORE trusting `embedding` → gather with `return_exceptions=True` so one unexpected error cannot abort the batch; bare exceptions are normalised into `ImageEmbeddingResult`s so callers only ever see the interface type.
**Invariant:** never trust the transport status on Titan — the body-level `message` field is the failure channel. Credentials missing at CLIENT-BUILD time raise typed `EmbeddingError` (constructor-level misconfiguration may raise); everything after that is per-image results.
**Probe:** deterministic pins (no dedicated suite at this pin — coverage caveat; consumer contract suite-tested via Jina): `grep -c 'while still returning HTTP 200' backend/python/app/services/embeddings/multimodal/bedrock_provider.py` == 1; `grep -c 'return_exceptions=True' <same>` == 2 (the explanatory comment and the `asyncio.gather` call site); `grep -n '_SUPPORTED_OUTPUT_EMBEDDING_LENGTHS = (256, 384, 1024)' <same>` == 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "BedrockMultimodalProvider outputEmbeddingLength invoke_model inputImage", limit: 10 });
```

## Verdict
Adopt the body-message failure channel + supported-length resolution-with-warning + return_exceptions normalisation; adapt credential handling and model ids; omit Titan specifics only if your host never speaks to Bedrock. Coverage caveat: pinned by deterministic source greps; no direct upstream spec for this class at `c28d133`.
