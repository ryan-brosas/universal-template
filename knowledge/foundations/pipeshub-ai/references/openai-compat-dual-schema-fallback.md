<!-- capsule-v2 -->
|# OpenAI-compat dual-schema fallback — how do you embed images through an endpoint whose multimodal dialect you don't know?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** When an "OpenAI-compatible" base URL may speak either the standard `/v1/embeddings` `input` schema OR vLLM's chat-`messages` extension, what is the try/fallback choreography?

## One input-schema attempt per batch, then per-image messages-mode gather; invalid images ride OUTSIDE both arms
**Path/Symbol:** `backend/python/app/services/embeddings/multimodal/openai_compat_provider.py` (whole file L1–186): constants :40–42 (`_CONCURRENCY_LIMIT=5`, `_BATCH_SIZE=16`, timeout 60s), `embed_images` :69–129, `process_batch` :76–116, `_post_input_format` :131–148, `_embed_via_messages` :150–178, `_as_data_uri` :181–186.
**Signature:** `async embed_images(self, image_base64s: list[str]) -> list[ImageEmbeddingResult]`; `async _post_input_format(...) -> object` (returns parsed `data` list); `async _embed_via_messages(client, endpoint, headers, index, uri) -> ImageEmbeddingResult`; `_as_data_uri(original: str, normalized: str) -> str`.
**Data Shape:** input arm: `{"model", "input": [data-uris], "encoding_format": "float"}` (batched ≤16). Messages arm: one image per request, chat content `[{"type":"image_url","image_url":{"url":uri}}]` + same `encoding_format` — vLLM's extension "never adopted the `input` schema and takes one image per request".

### Decisive source
```python
try:
    data = await self._post_input_format(client, endpoint, headers, [uri for _, uri in valid])
except Exception as standard_err:
    # vLLM's `messages` extension ... cannot batch.
    fallback = await asyncio.gather(*[
        self._embed_via_messages(client, endpoint, headers, index, uri)
        for index, uri in valid])
    if self.logger and any(r.embedding is None for r in fallback):
        self.logger.warning(f"... input-format error={describe_request_error(standard_err)}")
    return list(fallback) + invalid_results          # invalids APPENDED, not interleaved
return map_embedding_response(data, request_indices) + invalid_results
```

**Flow:** batches sliced by absolute start → per-batch normalise (invalid ⇒ immediate `"invalid image data"` results, held aside) → single POST in input format → on ANY exception, fan out one messages-mode POST per valid image (each individually caught into an error result) → concatenate. Docstring: there is "no universal standard", so failure is surfaced per-image rather than raised; a text-only server simply fails every image and the VLM-description fallback remains available.
**Invariant:** the input-format arm is tried ONCE PER BATCH (not per image); the fallback arm fires on ANY exception type (schema rejection, timeout, 4xx/5xx alike) because you cannot distinguish "wrong schema" from "server down" reliably — per-image errors carry whichever detail arrived last. Data-URI construction preserves an existing `data:` prefix verbatim and otherwise synthesizes `data:image/jpeg;base64,<normalized>`.
**Probe:** deterministic pins (this provider has no dedicated suite at pin — coverage caveat; shared mapping logic is suite-tested): `grep -c 'except Exception as standard_err' backend/python/app/services/embeddings/multimodal/openai_compat_provider.py` == 1; `grep -c vLLM <same>` == 3 (docstring, comment, warning text); `grep -c 'return f"data:image/jpeg;base64,{normalized}"' <same>` == 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "OpenAICompatMultimodalProvider embed_via_messages input format", limit: 10 });
```

## Verdict
Adopt the dual-dialect try/fallback shape (batched standard schema → per-image vLLM messages) and the append-invalids-after convention; adapt endpoint paths/auth header to host; omit LM Studio-specific labelling unless you route it too. Coverage caveat: pinned by deterministic source greps + the suite-tested `_response` helpers it calls; no direct spec for THIS class at `c28d133`.
