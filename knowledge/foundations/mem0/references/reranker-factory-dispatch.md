<!-- capsule-v2 -->
# RerankerFactory dispatch — string-keyed provider map with three-shape config normalization

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how does a config string like `{"reranker": {"provider": "cohere"}}` become a live reranker instance, and which inputs are rejected?

## Connected graph-selected seam
**Path/Symbol:** `mem0/utils/factory.py`: `RerankerFactory` (:226-285, `provider_to_class` :234-246, `create` :248-285); user-facing dialect `mem0/configs/rerankers/config.py:RerankerConfig` (provider + optional config dict, `extra="forbid"`).
**Signature:** `create(cls, provider_name: str, config: Optional[Union[BaseRerankerConfig, Dict]] = None, **kwargs)`.
**Data Shape:** five registered providers — `cohere`, `sentence_transformer`, `zero_entropy`, `llm_reranker`, `huggingface` — each mapping to (dotted class path, config class).

### Decisive source
```python
provider_to_class = {
    "cohere": ("mem0.reranker.cohere_reranker.CohereReranker", CohereRerankerConfig),
    ...
    "llm_reranker": ("mem0.reranker.llm_reranker.LLMReranker", LLMRerankerConfig),
    "huggingface": ("mem0.reranker.huggingface_reranker.HuggingFaceReranker", HuggingFaceRerankerConfig),
}
...
if provider_name not in cls.provider_to_class:
    raise ValueError(f"Unsupported reranker provider: {provider_name}")
class_path, config_class = cls.provider_to_class[provider_name]
if config is None:
    config = config_class(**kwargs)
elif isinstance(config, dict):
    config = config_class(**config, **kwargs)
elif not isinstance(config, BaseRerankerConfig):
    raise ValueError(f"Config must be a {config_class.__name__} instance or dict")
```

**Flow:** unknown provider ⇒ ValueError naming the input → None/dict/typed-config three-shape normalization (dicts merge with kwargs; non-Base objects REJECTED loudly rather than duck-typed) → importlib dotted-path load → constructor call. Note the registration asymmetry worth copying: the LLM reranker's provider key is `llm_reranker` while its config field default reads `openai`-style provider strings INSIDE `LLMRerankerConfig` — the outer key and inner provider are different namespaces.
**Invariant:** this factory is EAGER-validation at the boundary (bad provider/config die here, before any model/API construction), complementing the per-reranker lazy ImportError for missing SDKs — a port that moves validation into constructors loses the single choke-point error contract. The sibling factories (`LlmFactory`, `EmbedderFactory`, `VectorStoreFactory`) share this exact shape; this capsule pins the family pattern instance that pass 2's `factory-provider-resolution` generalized.
**Probe:** `grep -cF '"llm_reranker": ("mem0.reranker.llm_reranker.LLMReranker", LLMRerankerConfig),' mem0/utils/factory.py` (=1); `grep -cF 'raise ValueError(f"Unsupported reranker provider: {provider_name}")' mem0/utils/factory.py` (=1).
**Coverage caveat:** factory dispatch is exercised indirectly via main.py suites; no dedicated test file pins RerankerFactory itself.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "RerankerFactory provider_to_class create unsupported", limit: 10 });
```

## Verdict
Adopt the eager string-keyed dispatch + three-shape normalization for any pluggable-provider registry; adapt the provider roster to your backends; omit lazy per-constructor validation — the boundary is where bad configs must die.
