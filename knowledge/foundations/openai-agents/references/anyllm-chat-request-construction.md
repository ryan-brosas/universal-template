<!-- capsule-v2 -->
# AnyLLM chat request construction — how does one typed ModelSettings become a provider-safe chat-completions payload with per-provider header routing and no duplicate keys?

**Source:** openai-agents-python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** A porter building a chat-completions adapter must know the exact request-assembly order: message conversion, tool/format mapping, header routing per provider, logprobs gating, and escape-hatch precedence.

## _fetch_chat_response request assembly
**Path/Symbol:** `src/agents/extensions/models/any_llm_model.py:_fetch_chat_response` (:830–1005), `_build_chat_extra_kwargs` (:1364–1376), `_remove_not_given` (:1502–1505), `_merge_headers` (:1507–1514).
**Signature:** `async def _fetch_chat_response(self, *, system_instructions, input, model_settings, tools, output_schema, handoffs, span, tracing, stream: bool, prompt) -> ChatCompletion | tuple[Response, AsyncIterator[ChatCompletionChunk]]`.
**Data Shape:** Input: typed `ModelSettings` + Responses-item input list. Output: a raw `ChatCompletion` (non-streamed, normalized by `_normalize_chat_completion_response`) or a synthesized `Response` shell + chunk iterator (streamed).

### Decisive source
```python
if prompt is not None:
    raise UserError("AnyLLMModel does not currently support prompt-managed requests.")
preserve_thinking_blocks = (
    model_settings.reasoning is not None and model_settings.reasoning.effort is not None
)
converted_messages = Converter.items_to_messages(
    input, preserve_thinking_blocks=preserve_thinking_blocks,
    preserve_tool_output_all_content=True, model=self.model,
)
if any(name in self.model.lower() for name in ["anthropic", "claude", "gemini"]):
    converted_messages = self._fix_tool_message_ordering(converted_messages)
if system_instructions:
    converted_messages.insert(0, {"content": system_instructions, "role": "system"})
converted_messages = _to_dump_compatible(converted_messages)
...
if self._provider_name in {"gemini", "vertexai"}:
    # route headers into http_options (BaseModel copy / dict merge / create)
else:
    extra_kwargs["extra_headers"] = headers
if model_settings.top_logprobs is not None and "logprobs" not in extra_kwargs:
    extra_kwargs["logprobs"] = True
```
```python
def _build_chat_extra_kwargs(self, model_settings) -> dict[str, Any]:
    extra_kwargs: dict[str, Any] = {}
    if model_settings.extra_query is not None:
        extra_kwargs["extra_query"] = copy(model_settings.extra_query)
    if model_settings.metadata is not None:
        extra_kwargs["metadata"] = copy(model_settings.metadata)
    if model_settings.extra_body is not None:
        extra_kwargs["extra_body"] = copy(model_settings.extra_body)
    if model_settings.extra_args:
        extra_kwargs.update(model_settings.extra_args)
    return extra_kwargs
```

**Flow:** (1) prompt-managed requests fail loud with `UserError`; (2) `preserve_thinking_blocks` is gated on `reasoning.effort is not None` (a reasoning object without effort does not enable block preservation); (3) message conversion runs with `preserve_tool_output_all_content=True`; (4) `_fix_tool_message_ordering` runs ONLY for anthropic/claude/gemini model names (the one-tool-call-per-assistant-message repair from the anyllm-chat-path capsule); (5) system instructions insert at index 0; `_to_dump_compatible` materializes lazy values; (6) span input populated when `tracing.include_data()`; (7) tool_choice/response_format converted, tools converted + handoff tools appended, `parallel_tool_calls` forwarded only when converted_tools is non-empty; (8) `reasoning_effort` resolved from settings or extra_args, then POPPED from `extra_kwargs` after `_build_chat_extra_kwargs` so it is sent exactly once at top level; (9) headers: gemini/vertexai route into `http_options` (three shapes: pydantic `model_copy(update=...)`, dict merge, or fresh dict), everything else gets `extra_headers`; (10) `logprobs=True` auto-set only when `top_logprobs` is set AND the caller has not supplied `logprobs` via extra_args (defer, no duplicate-key collision); (11) `acompletion(...)` receives `self._remove_not_given(tool_choice/response_format)` (omit/NotGiven → None) and `converted_tools or None`; (12) non-streamed: raw-usage snapshot attached when `preserve_raw_usage`; streamed: a `Response` shell with `FAKE_RESPONSES_ID` and converted Responses tool_choice (defaulting to "auto") is returned with the chunk iterator.
**Invariant:** Escape-hatch precedence is fixed (extra_query < metadata < extra_body < extra_args-last) with copies at every boundary; promoted keys are removed from their origin; caller-supplied kwargs always win over SDK-derived ones; provider-specific header transport never leaks into other providers.
**Probe:** `tests/models/test_any_llm_model.py::test_any_llm_chat_sets_logprobs_when_top_logprobs_set` (:1638), `::test_any_llm_chat_omits_logprobs_when_top_logprobs_unset` (:1664), `::test_any_llm_google_chat_headers_use_http_options` (:419).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_fetch_chat_response _build_chat_extra_kwargs http_options extra_headers logprobs", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the assembly order and the three safety gates (prompt rejection, effort-gated thinking preservation, provider-conditional message repair). Adapt the header-transport split to your provider matrix (the gemini/vertexai `http_options` shapes are SDK-specific). Omit the FAKE_RESPONSES_ID shell only if your host has native streamed response objects. Coverage caveat: MCP not connected this pass; anchors verified by direct reads at HEAD fe45b415.
