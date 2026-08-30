<!-- capsule-v2 -->
# get_optional_params provider tail — how validated params reach a per-provider config class

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm` (MCP not connected at authoring time — direct source+test reading fallback, recorded in work record). **Question:** After the non-default-param validation ladder (sibling capsule optional-params-validation-ladder), which config class actually maps the params for a given provider, and what decides between model-list routing, route-prefix routing, and detection-model routing?

## The elif tail — three structural patterns
**Path/Symbol:** `litellm/utils.py` — `get_optional_params` elif chain (:4066-4517), terminal rungs (:4504-4517); route resolution `litellm/llms/bedrock/common_utils.py` — `BedrockModelInfo.get_bedrock_route` (:926-987).
**Signature:** each branch calls `<Provider>Config().map_openai_params(model=..., non_default_params=..., optional_params=..., drop_params=(drop_params if drop_params is not None and isinstance(drop_params, bool) else False))`.
**Data Shape:** input is the validated `non_default_params` dict from the pass-3 ladder; output is the provider-shaped `optional_params` dict that the dispatch helpers send to the API.

### Decisive source
```python
# utils.py:4139-4152 (abridged) — pattern (a): MODEL-LIST routing for vertex_ai
elif custom_llm_provider == "vertex_ai" and (
    model in litellm.vertex_chat_models or model in litellm.vertex_code_chat_models
    or model in litellm.vertex_text_models or ...
):
    optional_params = litellm.VertexGeminiConfig().map_openai_params(...)
...
# utils.py:4221-4231 (abridged) — pattern (b): ROUTE-BASED routing for bedrock
elif custom_llm_provider == "bedrock":
    bedrock_route: Final = BedrockModelInfo.get_bedrock_route(model)
    if bedrock_route == "converse" or bedrock_route == "converse_like":
        optional_params = litellm.AmazonConverseConfig().map_openai_params(...)
```

**Flow:** (a) Model-list routing — vertex_ai checks membership in six `litellm.vertex_*_models` lists → VertexGeminiConfig; `vertex_ai_beta` or `"gemini" in model` → VertexGeminiConfig; `VertexAIAnthropicConfig.is_supported_model` → anthropic config; else a nested ladder over vertex_mistral_models (with a codestral split to CodestralTextCompletionConfig), vertex_ai_ai21_models, the ProviderConfigManager result, and a generic VertexAILlama3Config fallback (:4175-4211). (b) Route-based routing — bedrock resolves `get_bedrock_route(model)` first: explicit route prefixes (`converse/`, `invoke/`, `mantle/`, `openai/`, `claude_platform/`, …) matched as LEADING PATH SEGMENTS so `bedrock_mantle/openai.gpt-5.5` is never mistaken for the `mantle/` route; then nova/nova-2 prefixes and application-inference-profile ARNs → converse; then converse-model-list membership → converse; default invoke. The tail then maps converse/converse_like → AmazonConverseConfig, openai → AmazonBedrockOpenAIConfig, anthropic+invoke → a legacy-name check splitting AmazonAnthropicConfig vs AmazonAnthropicClaudeConfig, else the ProviderConfigManager result (+ `map_claude_platform_auth_params` remap when route is claude_platform) (:4221-4264). (c) Detection-model routing — azure computes `_azure_detection_model = base_model or model` and runs o-series > gpt-5 > default, with an api_version ladder (param > litellm.api_version > AZURE_API_VERSION secret > AZURE_DEFAULT_API_VERSION) only on the default rung (:4469-4503). Quirks: the `anthropic_text` branch calls `AnthropicTextConfig().map_openai_params` TWICE in a row (:4075-4086 — idempotent, but a real code smell); watsonx raises ValueError AFTER mapping if any passed param is a watsonx_text param (endpoint-migration guard pointing users at the `watsonx_text` provider, :4442-4447). Terminal rungs: `elif provider_config is not None` (the ProviderConfigManager result computed at :3996-4001) → its map_openai_params; else OpenAILikeChatConfig (:4504-4517).
**Invariant:** Branch ORDER is the contract — the specific model-list/route/detection rungs must precede the generic `provider_config` and OpenAI-like fallbacks, or a manager-resolved config silently shadows the hand-written special case. Route prefixes match as path segments, never substrings (the bedrock_mantle regression pins this).
**Probe:** `tests/test_litellm/llms/vertex_ai/test_vertex.py` -k "test_vertex_tool_params or test_vertex_function_translation or test_vertex_tool_type_field_removal" executed live at the pin → 8 passed (all drive the vertex_ai gemini branch through `get_optional_params(model="gemini-1.5-pro", custom_llm_provider="vertex_ai", tools=...)`); `tests/test_litellm/llms/bedrock/test_bedrock_common_utils.py` -k "route" → 14 passed (incl. `test_route_prefix_matched_as_path_segment_not_substring` :325 pinning `bedrock_mantle/openai.gpt-5.5 != mantle`). Watsonx guard: source-read only — no direct test found in the tree (recorded as evidence gap).

## Post-chain fold — overrides and nested drops
**Path/Symbol:** `litellm/utils.py` — `_apply_openai_param_overrides` (:4585-4605); nested-drop block (:4533-4539); call sites after the chain (:4519-4531).
**Signature:** `_apply_openai_param_overrides(optional_params: dict, non_default_params: dict, allowed_openai_params: list) -> dict`.

### Decisive source
```python
# utils.py:4598-4604 — only caller-sent params are forwarded (issue #25697)
if allowed_openai_params:
    for param in allowed_openai_params:
        if param in optional_params:
            continue
        if param not in non_default_params:
            continue
        optional_params[param] = non_default_params.pop(param)
```

**Flow:** after the provider branch: (1) `add_provider_specific_params_to_optional_params` (sibling capsule provider-specific-params-extra-body); (2) `_apply_openai_param_overrides` copies caller-sent `allowed_openai_params` entries into optional_params — it deliberately does NOT write None for allowed params the caller did not send (the old behavior leaked `enable_thinking=None` into the openai SDK as an unexpected kwarg, issue #25697); (3) nested paths in `additional_drop_params` (e.g. dotted keys) are deleted via `delete_nested_value`.
**Invariant:** `allowed_openai_params` is an opt-in passthrough: forwarding is gated on the param being present in BOTH the allow-list AND the caller's actual params. Writing defaults for absent allowed params reopens the SDK-kwarg crash.
**Probe:** same live suites as above; the override function's contract is pinned by its docstring regression reference and read at :4585-4605 (no dedicated unit test located in-tree this pass — recorded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "get_optional_params map_openai_params custom_llm_provider",
  filePattern: "utils.py", limit: 20 });
// → surfaces the validation ladder head (:3943+) and the elif tail branches
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "get_bedrock_route route_mappings path segment",
  filePattern: "common_utils.py", limit: 10 });
// → rank-1 BedrockModelInfo.get_bedrock_route :926-987
```

## Verdict
Adopt the three-pattern dispatch taxonomy (model-list / route-prefix / detection-model) with the specific-before-generic branch order, the path-segment (not substring) prefix matching, and the caller-sent-only override forwarding. Adapt the concrete model lists, route tables, and api_version ladders to your provider set; keep the ProviderConfigManager-result rung before the openai-like catch-all so data-driven providers stay reachable. Omit the anthropic_text double-call (port once) and treat the watsonx post-map ValueError as the template for endpoint-migration guards. Coverage caveat: the watsonx guard and _apply_openai_param_overrides have no runnable direct test at the pin (vcr/backoff blocks + not located); both are source-read only.
