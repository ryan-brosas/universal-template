<!-- capsule-v2 -->
# Supported OpenAI params ladder — which request params a provider accepts before validation

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm`. **Question:** Given (model, provider, request_type), where does the authoritative list of supported OpenAI-style params come from, and how do `base_model` hints and unknown providers behave?

## get_supported_openai_params module + openai fallback
**Path/Symbol:** `litellm/litellm_core_utils/get_supported_openai_params.py:get_supported_openai_params` (:8-290, whole 290-line module); consumer/fallback site `litellm/utils.py:4051-4060` inside `get_optional_params`.
**Signature:** `get_supported_openai_params(model: str, custom_llm_provider: str | None = None, request_type: Literal["chat_completion", "embeddings", "transcription"] = "chat_completion", base_model: str | None = None) -> list | None`.
**Data Shape:** returns a list of param-name strings, or None when the provider is unmapped; `base_model` is an additive capability hint for deployments whose label isn't self-describing (Azure deployment names, Bedrock aliases).

### Decisive source
```python
# get_supported_openai_params.py:33-59 — inference, manager path, additive base_model union
if not custom_llm_provider:
    try:
        custom_llm_provider = litellm.get_llm_provider(model=model)[1]
    except BadRequestError:
        return None
if custom_llm_provider in LlmProvidersSet:
    provider_config = litellm.ProviderConfigManager.get_provider_chat_config(
        model=model, provider=LlmProviders(custom_llm_provider), base_model=base_model)
elif custom_llm_provider.split("/")[0] in LlmProvidersSet:
    ...  # prefixed alias falls back to its first path segment
else:
    provider_config = None
if provider_config and request_type == "chat_completion":
    supported_params = provider_config.get_supported_openai_params(model=model)
    if base_model and base_model != model:
        base_model_params: Final = provider_config.get_supported_openai_params(model=base_model)
        supported_params = list(dict.fromkeys([*supported_params, *base_model_params]))
    return supported_params
```
```python
# utils.py:4052-4060 — the None→openai fallback and per-request override
supported_params = get_supported_openai_params(
    model=model, custom_llm_provider=custom_llm_provider, base_model=base_model)
if supported_params is None:
    supported_params = get_supported_openai_params(model=model, custom_llm_provider="openai")
supported_params = supported_params or []
allowed_openai_params = allowed_openai_params or []
supported_params.extend(allowed_openai_params)
```

**Flow:** infer provider from the model string when absent (`BadRequestError` → None); primary path routes through `ProviderConfigManager.get_provider_chat_config`; a legacy elif chain (:61-289) still handles providers/branches outside the enum or needing per-`request_type` splits (bedrock converse, ollama twins, azure o-series/GPT-5 detection by model name, vertex model-prefix routing, transcription configs for openai/mistral/deepgram/…); `_custom_providers` registered at runtime resolve through the CUSTOM config. The consumer in `get_optional_params` turns None into a retry against `custom_llm_provider="openai"` — unknown providers are validated as if openai — then extends the list with `allowed_openai_params` before `_check_valid_arg` raises/drops.
**Invariant:** A hint can only ADD capabilities: the result is the order-preserving deduped union of model params + base_model params. None means "unmapped", never "supports nothing" — consumers must apply the openai fallback themselves.
**Probe:** `tests/test_litellm/litellm_core_utils/test_get_supported_openai_params.py` executed live at the pin → 10 passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "get_supported_openai_params supported openai params provider",
  fields: ["lines", "signature"], limit: 12 });
// → rank-1 exact: litellm_core_utils.get_supported_openai_params.get_supported_openai_params (8-290)
//   followed by per-provider Config methods (OpenAIConfig :168-190, MaritalkConfig :44-58, …)
await mcp.codebase_memory.trace_path({ project: "litellm", direction: "inbound",
  functionName: "litellm.litellm.litellm_core_utils.get_supported_openai_params.get_supported_openai_params" });
// → proxy supported_openai_params endpoint, Router._pre_call_checks/_set_model_group_info, responses transformation…
```

## Verdict
Adopt: single resolver returning list-or-None; additive capability-hint union with order-preserving dedup; explicit openai-fallback retry at the validation call site; `allowed_openai_params` as a per-request escape hatch. Adapt: the legacy elif chain is litellm's migration debt — new ports should register provider configs with the manager instead of extending elifs. Omit vendor-specific branches you don't port. Note for maintainers: this function moved OUT of utils.py into its own module — older references citing "utils.py get_supported_openai_params" are stale. Coverage caveat: none on cited paths (both no_recorded_issue).
