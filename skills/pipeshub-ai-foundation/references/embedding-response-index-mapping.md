<!-- capsule-v2 -->
|# Embedding-response index mapping — how do you attach response embeddings back to request images when servers reorder, omit, or drop entries?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Given the OpenAI-style `{"data": [{"index", "embedding"}]}` envelope, how is each response entry bound to the caller's original input index?

## Match on the response's OWN index field; arrival order only as fallback; uncovered positions become ERRORS, never disappear
**Path/Symbol:** `backend/python/app/services/embeddings/multimodal/_response.py` (whole file L1–74): `describe_request_error` :19–30, `map_embedding_response` :33–65, `_embedding_of` :68–74. Shared by Jina (`jina_provider.py` :89) and OpenAI-compat (`openai_compat_provider.py` :116, :176).
**Signature:** `map_embedding_response(data: object, request_indices: Sequence[int]) -> list[ImageEmbeddingResult]` — `request_indices[p]` is the caller-side index of the image SENT at position p.
**Data Shape:** non-list `data` ⇒ treated as empty; each item must be a dict; `item["index"]` accepted only if `int` AND not `bool` (bool subclasses int!); duplicates resolved FIRST-WINS via `setdefault`; output has exactly `len(request_indices)` results in request order.

### Decisive source
```python
items = data if isinstance(data, list) else []
by_position: dict[int, object] = {}
for arrival, item in enumerate(items):
    if not isinstance(item, dict):
        continue
    position = item.get("index")
    if not isinstance(position, int) or isinstance(position, bool):
        position = arrival                      # servers that omit `index`
    by_position.setdefault(position, item)

for position, original_index in enumerate(request_indices):
    embedding = _embedding_of(by_position.get(position))
    if embedding is None:
        results.append(ImageEmbeddingResult(index=original_index,
                                            error=_MISSING_EMBEDDING_ERROR))
    else:
        results.append(ImageEmbeddingResult(index=original_index, embedding=embedding))

def _embedding_of(item):
    ... if not isinstance(embedding, list) or not embedding: return None
```

**Flow:** provider slices its input into batches carrying absolute indices → POST → passes raw `data` + the batch's `request_indices` here → results appended after the batch's pre-built invalid-image results. Module docstring states why this lives centrally: "zipping ``data`` to the request list by position attaches an embedding to the wrong image whenever a server reorders or omits entries" — getting it wrong is SILENT.
**Invariant:** every requested position yields exactly one result (error-not-drop), because `IMultimodalEmbeddingProvider` forbids silently dropping inputs. An empty/non-list `embedding` value counts as missing. Error bodies are surfaced with up to 300 chars of response text (`describe_request_error`) because `str(HTTPStatusError)` names the status but never the cause ("422 Unprocessable Entity" alone is undiagnosable).
**Probe:** `backend/python/tests/unit/services/embeddings/multimodal/test_jina_provider.py::test_out_of_order_response_maps_by_index` (:138, regression: positional zip attached embeddings to WRONG images) and `::test_short_response_errors_the_unanswered_index` (:161) and `::test_http_error_surfaces_the_response_body` (:221).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "map_embedding_response describe_request_error", limit: 10 });
```

## Verdict
Adopt index-field matching with bool-exclusion, first-wins duplicate policy, arrival-order fallback, and error-per-uncovered-position; adapt the error-string constants; omit nothing else — this helper is fully portable as-is. Direct tests ship upstream (three Jina-suite regression tests exercise this exact function through `JinaMultimodalProvider.embed_images`).
