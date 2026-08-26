<!-- capsule-v2 -->
# Cross-encoder & embedder — LLM-as-judge reranking + embedding ABC

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how do you rerank passages without a trained cross-encoder (using an LLM's own token logprobs), and how are embedding providers abstracted?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/cross_encoder/client.py`: `CrossEncoderClient` (:20) — `rank(query, passages) -> list[(passage, score)]`; `openai_reranker_client.py`: `OpenAIRerankerClient.rank` (:61-115); also `bge_reranker_client.py` (local BGE model), `gemini_reranker_client.py`. `embedder/client.py`: `EmbedderConfig` (:26), `EmbedderClient` (:30) — `create` (:32), `create_batch` (:37); providers openai/gemini/azure/voyage.
**Signature:** `rank(query, passages)` — one judge call per passage, gathered under a semaphore; scores in [0,1].
**Data Shape:** judge prompt wraps passage+query in XML-ish tags; response constrained to a single token: `max_tokens=1`, `temperature=0`, `logit_bias={'6432': 1, '7983': 1}` (forces "True"/"False" token ids), `logprobs=True, top_logprobs=2`.

### Decisive source
```ts
async def rank(self, query, passages):
    # system: 'You are an expert tasked with determining whether the passage is relevant to the query'
    # user: Respond with "True" if PASSAGE is relevant to QUERY and "False" otherwise.
    responses = await semaphore_gather(*[
        self.client.chat.completions.create(
            model=..., messages=..., temperature=0, max_tokens=1,
            logit_bias={'6432': 1, '7983': 1},   # only True/False tokens possible
            logprobs=True, top_logprobs=2)
        for ... ])
    for top_logprobs in responses_top_logprobs:
        norm_logprobs = np.exp(top_logprobs[0].logprob)
        if top_logprobs[0].token.strip().split(' ')[0].lower() == 'true':
            scores.append(norm_logprobs)          # P(True) IS the relevance score
        else:
            scores.append(1 - norm_logprobs)      # P(False) inverted
```

**Flow:** each passage gets an independent boolean-relevance judge call → logit bias restricts output to True/False → `exp(logprob)` of the winning token converts to a calibrated probability; True → score = P(True); False → score = 1 − P(False). Calls run concurrently under `semaphore_gather`. The embedder ABC mirrors this portability: `create` / `create_batch` over OpenAI/Gemini/Azure/Voyage.
**Invariant:** ranking needs no trained cross-encoder model — any chat LLM works; scoring is probabilistic (logprobs), not binary; concurrency is bounded by a semaphore; the CrossEncoderClient/EmbedderClient ABCs let backends swap freely.
**Probe:** `tests/` cross-encoder tests (rank returns (passage, score) pairs sorted by relevance; logit-bias single-token responses parsed; bge local path matches interface).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "CrossEncoderClient rank logit_bias logprobs EmbedderClient create_batch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt LLM-as-judge reranking via logit-biased single-token calls with logprob-derived scores when no cross-encoder is available; adopt the thin EmbedderClient ABC for provider swaps. Adapt models/bias ids per host.
