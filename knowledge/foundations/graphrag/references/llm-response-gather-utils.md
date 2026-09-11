<!-- capsule-v2 -->
# Stream-gather & response-shaping kernels — how do streamed sub-answers collapse into one string and raw JSON become a typed model?

**Source:** graphrag (MIT) `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** Where is the single choke point that turns an LLM completion response-or-chunk-stream into text, and chunks of JSON into pydantic models?

## gather_completion_response twins + structure + mock embedding builder
**Path/Symbol:** `packages/graphrag-llm/graphrag_llm/utils/gather_completion_response.py`: `gather_completion_response` (:16-33), `gather_completion_response_async` (:36-57); `packages/graphrag-llm/graphrag_llm/utils/structure_response.py`: `structure_completion_response` (:14-29); `packages/graphrag-llm/graphrag_llm/utils/create_embedding_response.py`: `create_embedding_response` (:9-39, mock path; sole caller `MockLLMEmbedding.embedding/embedding_async`).
**Signature:** `gather_completion_response(response: LLMCompletionResponse | Iterator[LLMCompletionChunk]) -> str` (+async twin over AsyncIterator); `structure_completion_response(response: str, model: type[T]) -> T`; `create_embedding_response(embeddings: list[float], batch_size: int = 1) -> LLMEmbeddingResponse`.
**Data Shape:** chunk frame `chunk.choices[0].delta.content`; non-stream frame `response.choices[0].message.content`; both None-coalesced to "". Structured path: strict `json.loads` → `model(**parsed_dict)`.

### Decisive source
```python
# sync twin — the async twin mirrors this with `async for`
if isinstance(response, Iterator):
    return "".join(chunk.choices[0].delta.content or "" for chunk in response)
return response.choices[0].message.content or ""

# structured/json_mode choke point (mock :108, lite_llm :162/:201)
parsed_dict: dict[str, Any] = json.loads(response)
return model(**parsed_dict)          # raises raw json.JSONDecodeError / ValidationError — no wrapping

# mock embeddings: ONE source vector → N per-instance copies (pydantic validates/copies each field)
embeddings_objects = [LLMEmbedding(object="embedding", embedding=embeddings, index=index)
                      for index in range(batch_size)]   # model="mock-model", usage 0/0
```

**Flow:** every Map-Reduce fan-out collapses its streamed sub-answer through the gather twins — global_search/search.py:243, drift_search/search.py:402, rate_relevancy.py:65 all `await gather_completion_response_async(model_response)` before parsing. Structured outputs route through structure_completion_response at completion time.
**Invariant:** content extraction must None-coalesce (`or ""`) because providers emit null deltas between tokens; stream-vs-response is detected by Iterator/AsyncIterator isinstance — NOT by duck-typing length. PROBED invariants: `''.join` over `["he","llo",None,"!"]` → `'hello!'`; async generator `["a",None,"b"]` → `'ab'`; non-stream content=None → `''`. Mock embedding: `r.data[0].embedding is r.data[1].embedding` is **False** — one source vector, N INDEPENDENT copies with distinct indexes (pydantic copies on validation), usage always zeroed.
**Probe:** NO dedicated unit tests exist for these utils (no tests/unit/llm directory upstream — recorded caveat). Behavior pinned by EXECUTED semantic probes run PRE-WRITE via lane venv @pin (outputs quoted above).

## Get live surrounding code
**Retrieve:** (executed live; rank-line-exact)
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "gather_completion_response stream chunks completion", limit: 10 });
// rank#1 gather_completion_response :16-33; rank#2 gather_completion_response_async :36-57;
// ranks #3-#5 BaseSearch.stream_search / GlobalSearch / BasicSearch — the caller plane
```

## Verdict
Adopt the None-coalescing join and Iterator-detection split as THE normalization boundary for mixed stream/response provider output, and the no-wrap json→model structuring (let callers own decode errors). Adapt chunk frames to host SDK shapes. Omit the mock embedding builder unless building a fake provider — but keep its lesson: fabricate per-item copies, never share mutable vectors across response entries.
