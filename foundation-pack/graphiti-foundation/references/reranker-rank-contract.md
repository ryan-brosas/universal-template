<!-- capsule-v2 -->
# Reranker rank() contract — what must every CrossEncoderClient variant preserve, and where may failure semantics diverge?

**Source:** graphiti Apache-2.0 `main@993e081a`; Codebase Memory `graphiti`. **Question:** what is the invariant every `rank()` implementation must keep when swapping local models for API scorers?

## Three rank() implementations behind one ABC
**Path/Symbol:** `graphiti_core/cross_encoder/client.py:CrossEncoderClient` (class :20, `rank` :28-40, ABC); `bge_reranker_client.py:BGERerankerClient` (:34-54); `gemini_reranker_client.py:GeminiRerankerClient.rank` (:73-161); OpenAI logprobs judge covered separately in `cross-encoder-embedder`.
**Signature:** `async def rank(self, query: str, passages: list[str]) -> list[tuple[str, float]]`.
**Data Shape:** returns (passage, score) pairs, scores normalized to [0,1], sorted score-DESCENDING; length must equal len(passages).

### Decisive source
```python
# bge_reranker_client.py :38-54 — local sync model bridged into async:
async def rank(self, query, passages):
    if not passages:
        return []
    input_pairs = [[query, passage] for passage in passages]
    loop = asyncio.get_running_loop()
    scores = await loop.run_in_executor(None, self.model.predict, input_pairs)
    ranked_passages = sorted(
        [(passage, float(score)) for passage, score in zip(passages, scores, strict=False)],
        key=lambda x: x[1], reverse=True,
    )
    return ranked_passages
# gemini_reranker_client.py divergences (:79-80, :121, :127-137, :149-158):
#   len(passages) <= 1 -> [(p, 1.0) for p in passages]   # NOT []
zip(passages, responses, strict=True)                      # opposite zip strictness
#   re.search(r'\b(\d{1,3})\b', text) -> score/100 clamped [0,1]
#   parse-fail / empty -> results.append((passage, 0.0))    # never drops a passage
#   'rate limit'|'quota'|'resource_exhausted'|'429' in str(e) -> raise RateLimitError
```

**Flow:** BGE: `CrossEncoder('BAAI/bge-reranker-v2-m3')` eager-loaded in `__init__` (heavy download/instantiate at construction, not first rank) → empty short-circuit → pair matrix scored SYNCHRONOUSLY inside `run_in_executor(None, ...)` off the event loop → strict=False zip → sort desc. Gemini: singleton shortcut scores 1.0 → per-passage 0-100 prompts fanned out concurrently via `semaphore_gather` (O(n) API calls) → regex score extraction → /100 normalization with [0,1] clamp → unparsable responses become (passage, 0.0) WITH warning, never dropped → strict=True zip → sort desc → exception-string sniffing maps quota/rate-limit errors to the shared RateLimitError taxonomy.
**Invariant:** same-length output sorted descending is the contract reranker consumers rely on; the two variants reach it with OPPOSITE robustness choices — BGE tolerates score/passage misalignment silently (strict=False) while Gemini guarantees alignment (strict=True) and manufactures 0.0 scores rather than shrinking the list. Empty-input semantics: BOTH return [] for zero passages (Gemini's `len(passages) <= 1` shortcut subsumes it, pinned by test_rank_empty_passages :124-131); they DIVERGE at exactly one passage — BGE still runs the model, Gemini returns 1.0 WITHOUT any API call. Eager model load belongs in the CONSTRUCTOR so first-ranking latency stays predictable.
**Probe:** `pytest tests/cross_encoder/test_gemini_reranker_client.py -q` — mocked genai client (offline-capable), 17 passed this pass; pins init/config/custom-client wiring, score parsing incl. 0-100 → [0,1] normalization (:119-121 asserts 0.85/0.45/0.20), empty→[] (:124-131), single→1.0 no-call (:134-146), quota/429 mapping. BGE's direct test `tests/cross_encoder/test_bge_reranker_client_int.py` is integration-marked (downloads the real model) — coverage caveat; source read confirms its empty→[] and executor-bridge shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "BGERerankerClient GeminiRerankerClient rank run_in_executor semaphore_gather", limit: 10 });
```

## Verdict
Adopt the sorted-same-length contract and the executor bridge for synchronous local models. Adapt: choose zip strictness deliberately (strict=True + synthetic 0.0 for API scorers where response order is guaranteed; document any tolerance). Omit the singleton-equals-perfect shortcut unless downstream ranking tolerates ties at 1.0.
