<!-- capsule-v2 -->
# Factory provider resolution — how do 20+ backends plug in without eager imports or config-class mismatches?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how does the factory instantiate providers lazily and route base configs into provider-specific ones safely?

## Connected graph-selected seam
**Path/Symbol:** `mem0/utils/factory.py`: `load_class` (:29-32), `LlmFactory.create` (:64-125) + `register_provider` (:128-139), `EmbedderFactory.create` (:167-177), `VectorStoreFactory.create/reset` (:209-223), `RerankerFactory.create` (:244-280).
**Signature:** `create(provider_name, config=None, **kwargs)` per factory; `provider_to_class` maps name → `(class_path, config_class)` (embedder map is path-only).
**Data Shape:** config accepted as None (defaults+kwargs), dict (merged with kwargs then constructed), or base-config instance (converted field-by-field).

### Decisive source
```python
elif isinstance(config, BaseLlmConfig):
    if config_class != BaseLlmConfig:
        # Only forward reasoning fields to provider configs that accept them
        # (explicitly or via **kwargs); others would raise on unexpected kwargs.
        params = inspect.signature(config_class).parameters
        accepts_kwargs = any(p.kind == p.VAR_KEYWORD for p in params.values())
        if accepts_kwargs or "reasoning_effort" in params:
            config_dict["reasoning_effort"] = config.reasoning_effort
        if accepts_kwargs or "is_reasoning_model" in params:
            config_dict["is_reasoning_model"] = config.is_reasoning_model
```
```python
# EmbedderFactory — the store-owns-embedding special case:
if provider_name == "upstash_vector" and vector_config and vector_config.enable_embeddings:
    return MockEmbeddings()
```

**Flow:** registry lookup → lazy import via `module.rsplit(".", 1)` at CREATE time (adding a provider never costs an import until used) → config triage; LLM conversion whitelists reasoning fields by INTROSPECTING the target config's signature so old base configs don't explode new providers; unknown provider raises ValueError listing nothing (registry is the docs). VectorStoreFactory coerces pydantic configs via `model_dump()`; RerankerFactory raises ImportError-wrapped failures for missing optional deps.
**Invariant:** signature-introspection gating is what keeps N providers × M config versions compatible — forwarding a field a dataclass doesn't declare is a TypeError, not a warning; `register_provider` extends the registry at runtime (plugin point); embedder creation receives vector-store config because some stores embed server-side (MockEmbeddings stub).
**Probe:** `tests/utils/test_factory.py`; reasoning-field routing pinned in `tests/llms/test_openai.py::test_reasoning_effort_config_values` (:226) and `tests/llms/test_azure_openai.py::test_azure_config_accepts_reasoning_effort` (:224).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "LlmFactory create register_provider EmbedderFactory VectorStoreFactory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt string-keyed registry + lazy load_class + introspection-gated config conversion; adapt config classes; omit the provider roster itself (data, not mechanism).
