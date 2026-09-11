<!-- capsule-v2 -->
# ProviderConfigManager resolution — how a (model, provider) pair picks its config class

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm` (MCP not connected at authoring time — direct source+test reading fallback, recorded in work record). **Question:** When the params/validation plane asks "which config class handles this model on this provider", what is the exact resolution order — and where do model-string heuristics, base_model threading, and JSON-defined providers fit?

## get_provider_chat_config — special cases → lazy O(1) map → JSON fallback
**Path/Symbol:** `litellm/utils.py` — `ProviderConfigManager` (:7823-8121): `_PROVIDER_CONFIG_MAP` class attr (:7827), `_build_provider_config_map` (:7830-7994), `get_provider_chat_config` (:8072-8121); sub-resolvers `_get_azure_config` (:7996-8011), `_get_azure_ai_config` (:8013-8018), `_get_vertex_ai_config` (:8020-8040), `_get_bedrock_config` (:8042-8047), `_get_cohere_config` (:8049-8056).
**Signature:** `get_provider_chat_config(model: str, provider: LlmProviders, base_model: str | None = None) -> BaseConfig | None`.
**Data Shape:** map entries are `(factory lambda, needs_model: bool)` tuples keyed by `LlmProviders`; ~115 providers; `needs_model=True` for the model-string-keyed resolvers (AZURE_AI, VERTEX_AI, BEDROCK, COHERE/COHERE_CHAT).

### Decisive source
```python
# utils.py:8087-8109 (abridged) — rung order is load-bearing
if provider == LlmProviders.OPENAI:
    if litellm.openaiOSeriesConfig.is_model_o_series_model(model=model):
        return litellm.openaiOSeriesConfig          # module-level singleton
    if litellm.OpenAIGPT5Config.is_model_gpt_5_model(model=model):
        return litellm.OpenAIGPT5Config()
# Handle Azure before the generic map so base_model can be threaded through
if provider == LlmProviders.AZURE:
    return ProviderConfigManager._get_azure_config(model=model, base_model=base_model)
if ProviderConfigManager._PROVIDER_CONFIG_MAP is None:
    ProviderConfigManager._PROVIDER_CONFIG_MAP = ProviderConfigManager._build_provider_config_map()
config_entry = ProviderConfigManager._PROVIDER_CONFIG_MAP.get(provider)
if config_entry is not None:
    config_factory, needs_model = config_entry
    return config_factory(model) if needs_model else config_factory()
# utils.py:8111-8121 — JSON fallback, then None
if JSONProviderRegistry.exists(provider.value):
    provider_config = JSONProviderRegistry.get(provider.value)
    return create_config_class(provider_config)()
return None
```

**Flow:** (1) OpenAI special cases FIRST (o-series singleton, GPT-5 config) — before any map lookup; (2) Azure before the map so `base_model` threads through: `detection_model = base_model or model`, then o-series > gpt-5 > default `AzureOpenAIConfig` — this is what lets non-standard deployment names (`azure/my-deployment-id`) route correctly when the caller knows the true underlying model; (3) lazy map build on first access (avoids circular imports at module load); (4) map hit → factory with or without model; (5) miss → JSON provider registry (`litellm/llms/openai_like/json_loader.py` :1-88 — `providers.json` loaded once per process into `SimpleProviderConfig` dataclasses; `create_config_class(provider_config)()` synthesizes an OpenAI-compatible config class from the data); (6) else `None` — which the supported-openai-params consumer turns into its openai-fallback retry (see sibling capsule).
**Invariant:** Rung order is part of the contract: moving Azure into the map would lose base_model threading; returning a shared mutable singleton (the o-series case returns the module-level `openaiOSeriesConfig`) is intentional — config objects are stateless. `None` means "unmapped", never "use default provider behavior".
**Probe:** `tests/test_litellm/llms/azure/chat/test_azure_base_model_routing.py` executed live at the pin → 25 passed (pins base_model detection for gpt-5/o-series/default, fallback to model when base_model is None, and get_provider_chat_config threading); `tests/test_litellm/llms/openai_like/test_json_providers.py` → 18 passed, 4 skipped (pins the JSON-fallback rung).

## Model-string-keyed sub-resolvers
**Path/Symbol:** `litellm/utils.py` — `_get_vertex_ai_config` (:8020-8040), `_get_bedrock_config` (:8042-8047).
**Signature:** `_get_vertex_ai_config(model: str) -> BaseConfig`.

### Decisive source
```python
# utils.py:8021-8040 (abridged) — substring/membership ladder over the MODEL STRING
if "gemini" in model:
    return litellm.VertexGeminiConfig()
elif "claude" in model:
    return litellm.VertexAIAnthropicConfig()
elif "gpt-oss" in model:
    return VertexAIGPTOSSTransformation()
elif model in litellm.vertex_mistral_models:
    if "codestral" in model:
        return litellm.CodestralTextCompletionConfig()
    return litellm.MistralConfig()
elif model in litellm.vertex_ai_ai21_models:
    return litellm.VertexAIAi21Config()
else:
    return litellm.VertexAILlama3Config()
```

**Flow:** vertex resolves by substring/membership ladder over the model string (gemini > claude > gpt-oss > mistral/codestral > ai21 > llama3 default); bedrock delegates to `get_bedrock_chat_config(model)` which resolves the config class FROM THE MODEL STRING (same pattern as the pass-4 modality-variants capsule's bedrock image-gen branch).
**Invariant:** These ladders are ORDERED — first match wins, so adding a new partner model means inserting its rung ABOVE the catch-all, not below. The final else is a real default (llama3), not an error.
**Probe:** covered by the 25-passed azure routing suite for the base_model plane; vertex/bedrock ladder confirmed by source read (their direct suites are provider-specific transformation tests not re-run this pass).

## get_provider_embedding_config — the legacy elif chain
**Path/Symbol:** `litellm/utils.py` — `ProviderConfigManager.get_provider_embedding_config` (:8123-8208).
**Signature:** `get_provider_embedding_config(model: str, provider: LlmProviders) -> BaseEmbeddingConfig | None`.

### Decisive source
```python
# utils.py:8128-8139 (abridged) — voyage splits by model BEFORE the plain config
if litellm.LlmProviders.VOYAGE == provider and litellm.VoyageContextualEmbeddingConfig.is_contextualized_embeddings(model):
    return litellm.VoyageContextualEmbeddingConfig()
elif litellm.LlmProviders.VOYAGE == provider and litellm.VoyageMultimodalEmbeddingConfig.is_multimodal_embeddings(model):
    return litellm.VoyageMultimodalEmbeddingConfig()
elif litellm.LlmProviders.VOYAGE == provider:
    return litellm.VoyageEmbeddingConfig()
...  # ~20 more providers, each a flat elif ...
return None
```

**Flow:** flat elif chain (~20 providers) with no map; model-dependent providers (voyage contextual/multimodal, sagemaker `SagemakerEmbeddingConfig.get_model_config(model)`) check the model string inside their rung; unmapped providers return None.
**Invariant:** This is the OLD pattern the chat-config map replaced — when porting, use the map shape for chat and treat this chain as evidence of what the migration looks like mid-flight (both coexist in one class).
**Probe:** source read; adjacent live evidence is the pass-4 embeddings modality suite (17 passed) which consumes these configs through `get_optional_params_embeddings`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "ProviderConfigManager get_provider_chat_config _build_provider_config_map",
  filePattern: "utils.py", limit: 20 });
// → rank-1..n surface the manager :7823, map builder :7830, entry point :8072, embedding twin :8123
```

## Verdict
Adopt the four-rung resolution (provider special cases → lazy O(1) factory map with needs_model flag → data-driven JSON fallback → explicit None) and the base_model-threading carve-out for deployment-name indirection; adopt ordered substring ladders for multi-model-host providers with a real default at the bottom. Adapt the JSON provider schema (`base_url`, `api_key_env`, `param_mappings`, `constraints`, `supported_endpoints`) to your own provider-descriptor format. Omit the per-modality legacy elif chains as targets — they are migration debt, not design. Coverage caveat: MCP graph retrieval not available this session; all line anchors verified by direct read at the pin.
