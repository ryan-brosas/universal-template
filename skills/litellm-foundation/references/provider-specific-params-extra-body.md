<!-- capsule-v2 -->
# Provider-specific params → extra_body — how unknown caller params survive the validation ladder

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm` (MCP not connected at authoring time — direct source+test reading fallback, recorded in work record). **Question:** After the drop-or-UnsupportedParamsError ladder (sibling capsule) has validated known params, what happens to params the provider doesn't know about — and why do OpenAI-family providers route them into `extra_body` while everyone else gets a flat copy?

## add_provider_specific_params_to_optional_params — the two-branch fold
**Path/Symbol:** `litellm/utils.py` — `add_provider_specific_params_to_optional_params` (:4544-4582); gate `_should_drop_param` (:2991-2995); safety pass `_ensure_extra_body_is_safe` in `litellm/litellm_core_utils/llm_request_utils.py` (:6-30). Call sites: `get_optional_params` :4519, `pre_process_non_default_params` :3838 (flag-gated by `add_provider_specific_params`), and the three modality variants `get_optional_params_transcription` :3089 / `get_optional_params_image_gen` :3228 / `get_optional_params_embeddings` :3583.
**Signature:** `add_provider_specific_params_to_optional_params(optional_params: dict, passed_params: dict, custom_llm_provider: str, openai_params: list[str], additional_drop_params: list | None = None) -> dict`.
**Data Shape:** mutates BOTH inputs — `passed_params.pop("extra_body")` consumes the caller's extra_body, and unknown keys are removed from `passed_params`'s consideration by being copied into `optional_params`; `openai_params` is the modality's default-param key list (e.g. `list(DEFAULT_EMBEDDING_PARAM_VALUES.keys())`).

### Decisive source
```python
# utils.py:4555-4581 (abridged)
if custom_llm_provider in ["openai", "azure", "text-completion-openai"] + litellm.openai_compatible_providers:
    # for openai, azure we should pass the extra/passed params within `extra_body`
    if _should_drop_param(k="extra_body", additional_drop_params=additional_drop_params) is False:
        extra_body = dict(passed_params.pop("extra_body", None) or {})
        for k in passed_params:
            if k not in openai_params and passed_params[k] is not None:
                extra_body[k] = passed_params[k]
        ...
        optional_params["extra_body"] = _ensure_extra_body_is_safe(extra_body=processed_extra_body)
else:
    for k in passed_params:
        if k not in openai_params and passed_params[k] is not None:
            if _should_drop_param(k=k, additional_drop_params=additional_drop_params):
                continue
            optional_params[k] = passed_params[k]
return optional_params
```

**Flow:** branch 1 (openai/azure/text-completion-openai + `litellm.openai_compatible_providers`): the caller's explicit `extra_body` (popped from passed_params, `None` normalized to `{}`) is merged with every unknown non-None param, existing `optional_params["extra_body"]` wins as the base, `additional_drop_params` filters the merged dict, then `_ensure_extra_body_is_safe` runs. Branch 2 (every other provider): unknown non-None params are copied FLAT onto optional_params one by one, each individually gated by `_should_drop_param`.
**Invariant:** `extra_body=None` must never crash the fold (`dict(... or {})` — regression pinned live below). The safety pass exists because users embed Langfuse `TextPromptClient` objects in `metadata.prompt`, which are not JSON-serializable (issue #4140): any object with `__dict__` under `metadata.prompt` is converted to its `__dict__`. The drop gate applies to the WHOLE extra_body in branch 1 but PER PARAM in branch 2 — that asymmetry fixed the bedrock `prompt_cache_key` leak (OpenAI-only params reaching Bedrock).
**Probe:** `tests/test_litellm/llms/hosted_vllm/responses/test_hosted_vllm_responses.py` executed live at the pin → 7 passed, incl. `test_hosted_vllm_responses_create_with_explicit_none_extra_body` (:97-115) which pins the `extra_body=None` non-crash through a real `get_optional_params` call. Direct per-param drop tests `tests/test_litellm/test_utils.py::TestAdditionalDropParams*` (:3391-3496, bedrock prompt_cache_key regression) BLOCKED this pass by missing `backoff` at collection import (re-observed).

## _should_drop_param — the per-model opt-out list
**Path/Symbol:** `litellm/utils.py` — `_should_drop_param` (:2991-2995); also consulted by `_get_non_default_params` (:2998-3008) so dropped params never even enter the non-default set.
**Signature:** `_should_drop_param(k, additional_drop_params) -> bool`.

### Decisive source
```python
# utils.py:2991-2995
def _should_drop_param(k, additional_drop_params) -> bool:
    if additional_drop_params is not None and isinstance(additional_drop_params, list) and k in additional_drop_params:
        return True  # allow user to drop specific params for a model - e.g. vllm - logit bias
    return False
```

**Flow:** membership test against the caller-supplied `additional_drop_params` list (threaded from `kwargs["additional_drop_params"]` at every call site); `None` or non-list means drop nothing.
**Invariant:** The list is an OPT-OUT, not an allow-list — everything not named passes through. It is consulted at two layers (non-default extraction AND provider-specific fold), so a dropped param leaves no trace in either output.
**Probe:** same live suite as above (hosted_vllm 7 passed exercises the fold path); the dedicated drop-list tests remain backoff-blocked (recorded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "add_provider_specific_params_to_optional_params _should_drop_param _ensure_extra_body_is_safe",
  limit: 20 });
// → rank-1..n surface the fold :4544, the gate :2991, the safety pass (llm_request_utils.py :6), and all five call sites
```

## Verdict
Adopt the two-branch fold (SDK-wrapped providers get a nested `extra_body` because their SDKs only accept known kwargs plus an escape hatch; raw-HTTP providers get flat keys), the `None`-safe extra_body normalization, the per-param vs whole-body drop asymmetry, and the two-layer drop consultation. Adapt the openai-compatible provider list to your own SDK-wrapped set, and the `__dict__` coercion to whatever non-serializable objects your users embed. Omit the Langfuse-specific metadata.prompt handling unless you support that client. Coverage caveat: the direct additional_drop_params unit tests (test_utils.py :3391-3496) are blocked by a missing `backoff` dependency in this environment; behavior confirmed by source read plus the live hosted_vllm suite.
