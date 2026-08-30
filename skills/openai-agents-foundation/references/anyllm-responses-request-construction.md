<!-- capsule-v2 -->
# AnyLLM Responses request construction — how do you assemble a validated Responses-API payload while routing transport kwargs around a strict public-API validator?

**Source:** openai-agents-python MIT `main@fe45b415ee05`; Codebase Memory `openai-agents-python`. **Question:** A porter building a Responses-API adapter over a validating third-party SDK must know the exact payload assembly order, the replay-input sanitization, and why transport kwargs go through a private method.

## Payload assembly ladder
**Path/Symbol:** `src/agents/extensions/models/any_llm_model.py:_fetch_responses_response` (:1040–1145) with `_build_responses_extra_kwargs` (:1376), `_build_responses_transport_kwargs` (:1388), `_call_any_llm_responses` (:1395), `_make_any_llm_responses_params` (:1436), `_sanitize_any_llm_responses_input` (:1445).
**Signature:** `async def _fetch_responses_response(*, system_instructions, input, model_settings, tools, output_schema, handoffs, previous_response_id, conversation_id, stream: bool, prompt) -> Response | AsyncIterator[ResponseStreamEvent]`.
**Data Shape:** input flows `ItemHelpers.input_to_new_input_list` → `_to_dump_compatible` (materialize lazy iterables) → `_sanitize_any_llm_responses_input` (recursive strip). `request_kwargs` is one flat dict; `transport_kwargs` is split out; both feed `_call_any_llm_responses`.

### Decisive source
```python
if prompt is not None:
    raise UserError("AnyLLMModel does not currently support prompt-managed requests.")
if not self._supports_responses():
    raise UserError(f"Provider '{self._provider_name}' does not support the Responses API.")
...
include_set = set(converted_tools.includes)
if model_settings.response_include is not None:
    include_set.update(_coerce_response_includables(model_settings.response_include))
if model_settings.top_logprobs is not None:
    include_set.add("message.output_text.logprobs")
include = list(include_set) or None
...
"reasoning": model_settings.reasoning.model_dump(mode="json", exclude_none=True)
if model_settings.reasoning is not None else None,
"text": self._remove_not_given(text),
**self._build_responses_extra_kwargs(model_settings),
```

**Flow:** fail-fast gates (prompt unsupported, capability unsupported) → input normalization chain → tool/tool_choice conversion + materialization → include-set union (converted-tools includes ∪ response_include ∪ logprobs-include when top_logprobs set) → verbosity merged into `text` (create the dict if it is `omit`) → flat request_kwargs with `reasoning` dumped as a MAPPING (`model_dump(mode="json", exclude_none=True)`) → transport kwargs split → private-API call → non-stream responses normalized + optional raw-usage snapshot.
**Invariant:** `reasoning` must be a mapping, never a pydantic pair-list (any-llm types `ResponsesParams.reasoning` as a mapping; a pair list fails validation before the provider is reached). `tool_choice` and `text` pass through `_remove_not_given` so `omit` sentinels never reach the wire.
**Probe:** `tests/models/test_any_llm_model.py::test_any_llm_responses_path_sends_reasoning_as_a_mapping` (params.reasoning == {"effort": "low", "summary": "concise"}) and `::test_any_llm_responses_path_omits_reasoning_when_unset` (params.reasoning is None).

## Private-API transport escape
**Path/Symbol:** `src/agents/extensions/models/any_llm_model.py:_call_any_llm_responses` (:1395–1434).
**Signature:** splits `request_kwargs` into `params_payload` (keys in `_ANY_LLM_RESPONSES_PARAM_FIELDS`, module constant :108) and `provider_kwargs` (the rest), then `provider._aresponses(self._make_any_llm_responses_params(params_payload), **provider_kwargs)`.
**Data Shape:** no transport kwargs ⇒ public `provider.aresponses(model=..., input_data=..., **rest)`; any transport kwargs (e.g. `extra_headers` from `_merge_headers`) ⇒ private path.

### Decisive source
```python
# any-llm 1.11.0 validates public `aresponses()` kwargs against ResponsesParams,
# which rejects OpenAI transport kwargs like `extra_headers`. Build the params
# model ourselves so we can still pass transport kwargs through to the provider.
response = await provider._aresponses(
    self._make_any_llm_responses_params(params_payload),
    **provider_kwargs,
)
```

**Flow:** headers merged from model_settings → `transport_kwargs["extra_headers"]` → kwargs partition → params model built (`_make_any_llm_responses_params` falls back to a local `_AnyLLMResponsesParamsShim` when `any_llm.types.responses` is unimportable) → private call.
**Invariant:** the public `aresponses` is never called with non-param kwargs; the private path is only taken when transport kwargs exist; the params model is constructed by the adapter so validation happens on adapter terms.
**Probe:** `tests/models/test_any_llm_model.py::test_any_llm_responses_path_passes_transport_kwargs_via_private_provider_api` (public `responses_calls` empty; private call kwargs carry extra_headers/extra_query/extra_body).

## Replay-input sanitization
**Path/Symbol:** `src/agents/extensions/models/any_llm_model.py:_sanitize_any_llm_responses_input` / `_sanitize_any_llm_responses_value` (:1445–1493).
**Signature:** recursive dict/list walk returning a cleaned copy; drops `provider_data` keys, `id == FAKE_RESPONSES_ID`, all None values, and ENTIRE reasoning items that carry `provider_data`.
**Data Shape:** returns a new list; original untouched; non-dict leaves pass through.

### Decisive source
```python
# Provider-specific reasoning payloads are not replay-safe across adapter boundaries.
if value.get("type") == "reasoning" and value.get("provider_data"):
    return None
cleaned: dict[str, Any] = {}
for key, item_value in value.items():
    if key == "provider_data":
        continue
    if key == "id" and item_value == FAKE_RESPONSES_ID:
        continue
    if item_value is None:
        continue
```

**Flow:** SDK-produced replay items legitimately carry adapter-only fields (`provider_data`, `status=None`) that any-llm's OpenAI-style input models reject; the sanitizer strips them while preserving valid replay content, then the test re-validates the cleaned list through the real `ResponsesParams`.
**Invariant:** sanitization is subtractive-only (never invents content); reasoning items with provider payloads are dropped whole, not partially cleaned.
**Probe:** `tests/models/test_any_llm_model.py::test_any_llm_responses_input_sanitizer_strips_none_fields_from_reasoning_items` (cleaned dict equality + `ResponsesParams(model="dummy", input=cleaned)` validates) and `::test_any_llm_responses_path_sanitizes_replayed_items_before_validation` (public `aresponses` raises AssertionError if used; private call receives sanitized params).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_fetch_responses_response _call_any_llm_responses _sanitize_any_llm_responses_input", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-fast capability gates, the include-set union, the mapping-typed reasoning dump, and the subtractive replay sanitizer. Adopt the private-API transport escape when your target SDK validates public kwargs against a closed params model. Adapt the param-field partition constant and the params shim to the target SDK's actual schema. Omit the any-llm version pin commentary. Coverage caveat: MCP not connected this pass; citations verified by direct source+test reads at fe45b415ee05 with grep -n line anchors re-checked before writing.
