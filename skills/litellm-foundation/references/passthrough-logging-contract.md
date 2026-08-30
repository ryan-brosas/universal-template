<!-- capsule-v2 -->
# Passthrough logging contract — normalize_logging_result and logging_non_streaming_response

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm` (MCP not connected at authoring time — direct source+test reading fallback, recorded in work record). **Question:** How does the logging plane recover usage/cost from a raw httpx.Response returned by pass-through endpoints (which never produce a ModelResponse), and what is the provider-side contract for doing it?

## The normalization branch — where raw responses become loggable results
**Path/Symbol:** `litellm/litellm_core_utils/litellm_logging.py` — `Logging.normalize_logging_result` (:1903-1937); call site in `_success_handler_helper_fn` (:2078-2088); config lookup `litellm/utils.py` — `ProviderConfigManager.get_provider_passthrough_config` (:8618-8646).
**Signature:** `normalize_logging_result(self, result: Any) -> object`; `get_provider_passthrough_config(model: str, provider: LlmProviders) -> BasePassthroughConfig | None`.

### Decisive source
```python
# litellm_logging.py:1918-1936 (abridged)
elif (self.call_type == CallTypes.llm_passthrough_route.value
      or self.call_type == CallTypes.allm_passthrough_route.value) and isinstance(result, Response):
    provider_config: Final = ProviderConfigManager.get_provider_passthrough_config(
        provider=self.model_call_details.get("custom_llm_provider", ""), model=self.model)
    if provider_config is not None:
        logging_result = provider_config.logging_non_streaming_response(
            model=self.model, custom_llm_provider=..., httpx_response=result,
            request_data=self.model_call_details.get("request_data", {}),
            logging_obj=self, endpoint=self.model_call_details.get("endpoint", ""))
return logging_result
```

**Flow:** `normalize_logging_result` runs inside the shared success helper (sibling capsule logging-callback-gate-and-payload-helpers) BEFORE cost computation, converting non-standard success results to something the cost machinery understands. Two branches: realtime call_type with a list result → RealtimeAPITokenUsageProcessor folds the stream's usage into a logging object (deferred — separate subsystem); llm/allm_passthrough_route with an httpx.Response → look up the provider's passthrough config (only bedrock / vllm / hosted_vllm / azure / watsonx have one; everything else returns None and the raw Response passes through untouched) and call its `logging_non_streaming_response`. The normalized result then flows into `_process_hidden_params_and_response_cost` exactly like a ModelResponse (:2080-2088), so usage/cost recovery is identical downstream.
**Invariant:** Normalization is a pure result-shape concern owned by the SHARED helper — both sync and async success bodies get it for free. A passthrough provider without a config must degrade to the raw response, not fail logging.
**Probe:** `tests/test_litellm/llms/azure/passthrough/test_azure_passthrough_transformation.py` executed live at the pin → 2 passed (`test_azure_passthrough_logging_non_streaming_response_chat_completions` :47 drives the happy path; `test_azure_passthrough_logging_non_streaming_response_unknown_endpoint_returns_none` :76 pins the None degradation).

## The provider contract — re-running transform_response over the raw body
**Path/Symbol:** `litellm/llms/base_llm/passthrough/transformation.py` — `BasePassthroughConfig.logging_non_streaming_response` (:98-107, default `pass`); `litellm/llms/azure/passthrough/transformation.py` (:87-117); `litellm/llms/bedrock/passthrough/transformation.py` (:114-155).
**Signature:** `logging_non_streaming_response(model, custom_llm_provider, httpx_response: Response, request_data: dict, logging_obj, endpoint) -> Optional[CostResponseTypes]`.

### Decisive source
```python
# azure/passthrough/transformation.py:100-116 (abridged)
if "chat/completions" not in endpoint:
    return None
openai_chat_config: Final = OpenAIGPTConfig()
litellm_model_response: Final[ModelResponse] = openai_chat_config.transform_response(
    model=model,
    messages=[{"role": "user", "content": "no-message-pass-through-endpoint"}],
    raw_response=httpx_response, model_response=ModelResponse(),
    logging_obj=logging_obj, optional_params={}, litellm_params={}, api_key="",
    request_data=request_data, encoding=encoding)
return litellm_model_response
...
# bedrock/passthrough/transformation.py:127-137 (abridged)
if "invoke" in endpoint:
    chat_config_model = "invoke/" + model
elif "converse" in endpoint:
    chat_config_model = "converse/" + model
else:
    return None
provider_chat_config: Final = ProviderConfigManager.get_provider_chat_config(
    provider=LlmProviders(custom_llm_provider), model=chat_config_model)
```

**Flow:** each implementation gates on ENDPOINT first (azure: "chat/completions" substring; bedrock: invoke/converse substring, which also selects WHICH chat config to reuse via the "invoke/"+model or "converse/"+model route-prefixed name — the same route vocabulary as the bedrock param-mapping capsule). Then it re-runs the provider's normal chat `transform_response` over the RAW httpx response with a sentinel user message ("no-message-pass-through-endpoint") and empty optional/litellm params — the transform's usage-extraction path is what produces the ModelResponse carrying token counts, from which the shared helper computes cost. Bedrock raises ValueError if no chat config resolves for the route-prefixed model; azure simply returns None for non-chat endpoints.
**Invariant:** The sentinel message exists because transform_response requires a messages argument but the request body was already sent — the content is never used for anything observable. Endpoint gating before any parsing keeps non-chat passthrough traffic (files, embeddings, etc.) out of the chat transform entirely.
**Probe:** live 2-passed suite above; the bedrock variant read at :114-155 (no dedicated bedrock passthrough-logging unit test located in-tree this pass — recorded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "normalize_logging_result logging_non_streaming_response",
  filePattern: "litellm_logging.py", limit: 10 });
// → rank-1 Logging.normalize_logging_result :1903-1937
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "logging_non_streaming_response transform_response no-message-pass-through-endpoint",
  limit: 20 });
// → the azure/bedrock implementations + the base-class no-op
```

## Verdict
Adopt the two-part contract: a normalization branch in the SHARED success helper keyed on (call_type, result type) that degrades to the raw result when no provider config exists, and a provider-side hook that endpoint-gates first, then reuses the normal chat transform over the raw response with a sentinel message to recover usage. Keep the base-class default a silent None/pass so new passthrough providers opt in explicitly. Adapt the endpoint substrings and the route-prefixed config selection to your provider set. Omit the realtime branch unless you port realtime usage folding (recorded as next-pass target). Coverage caveat: bedrock variant is source-read only this pass (no located direct test); azure path fully test-proven.
