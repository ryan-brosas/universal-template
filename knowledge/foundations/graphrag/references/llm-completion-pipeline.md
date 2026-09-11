<!-- capsule-v2 -->
# LLM completion pipeline — one ABC composing cache, retry, rate-limit, metrics

**Source:** graphrag MIT `<branch>@<commit>`; Codebase Memory `graphrag`. **Question:** how does a production LLM layer compose orthogonal concerns (caching, retry, throttling, metrics) around a single completion call instead of scattering them?

## Connected graph-selected seam
**Path/Symbol:** `graphrag_llm/completion/completion.py`: `LLMCompletion` (ABC :34) — constructor takes every cross-cutting dependency; `completion/lite_llm_completion.py`: `LiteLLMCompletion` (:24-93+) holds `_cache`, `_cache_key_creator`, `_rate_limiter`, `_retrier`, `_metrics_store`, `_metrics_processor`, `_track_metrics`; `completion/completion_factory.py`: `register_completion` (:36), `create_completion` (:55); types in `types/types.py` (`LLMCompletionFunction` Protocol :153, `LLMCompletionResponse` :86).
**Signature:** `create_completion(model_config, *, cache?, cache_key_creator?, tokenizer?) -> LLMCompletion` — factory resolves provider strategy (`LLMProviderType.LiteLLM` etc.), injects defaults; the ABC's constructor signature IS the composition contract.
**Data Shape:** `ModelConfig {model_provider, model, type, model_extra}`; model_id = `"{provider}/{model}"`; response extends the OpenAI `ChatCompletion` shape so downstream code stays provider-neutral.

### Decisive source
```ts
class LLMCompletion(ABC):
    @abstractmethod
    def __init__(self, *, model_id, model_config, tokenizer,
                 metrics_store, metrics_processor=None,
                 rate_limiter=None, retrier=None,
                 cache=None, cache_key_creator): ...
# call path (lite_llm_completion):
#   cache hit? (cache_key_creator(args)) -> return cached
#   else: rate_limiter.acquire(tokens): retrier(lambda: client.chat(...))
#         -> metrics_processor(record usage) -> maybe cache put -> return
```

**Flow:** config → factory picks backend + registers custom strategies via `register_completion(type, initializer)` → each call checks cache first (key from args via injectable `CacheKeyCreator`) → on miss: acquire rate-limit budget → retry-wrapped provider call (LiteLLM under the hood) → record token/latency metrics into `MetricsStore` → optionally store the result.
**Invariant:** every concern is optional and injected (None = disabled) — the ABC degrades to a bare passthrough; caching happens BEFORE rate limiting (a cache hit spends no quota); all backends speak the OpenAI response shape.
**Probe:** `tests/` llm tests (cache short-circuits before limiter; retry retries only transient errors; metrics recorded per call; mock_llm_completion for tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "LLMCompletion LiteLLMCompletion create_completion cache rate_limiter retrier metrics", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the injected-concerns ABC (cache/retry/rate-limit/metrics as optional constructor deps, checked in that order); adapt the factory registration to host providers.
