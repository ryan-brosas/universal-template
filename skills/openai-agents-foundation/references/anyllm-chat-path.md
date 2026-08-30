<!-- capsule-v2 -->
# AnyLLM chat path — how does a chat-completions adapter turn provider quirks into safe SDK outputs and spans?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When the Responses API is unavailable and the adapter must speak chat completions, how are missing usage, content-filter terminations, multi-tool assistant messages, and signed thinking blocks handled without corrupting SDK state?

## Non-streaming chat response assembly
**Path/Symbol:** `src/agents/extensions/models/any_llm_model.py:` `_get_response_via_chat` (:571–706), `_normalize_any_llm_message` (:224–252).
**Signature:** `async def _get_response_via_chat(self, *, system_instructions, input, model_settings, tools, output_schema, handoffs, tracing, prompt) -> ModelResponse`.
**Data Shape:** returns `ModelResponse(output=items, usage=usage, response_id=None, raw_usage=snapshot|None)`; span usage is a plain dict of ints plus detail-model dumps.

### Decisive source
```python
usage = (Usage(requests=1, input_tokens=response.usage.prompt_tokens, ...)
         if response.usage is not None
         # The request completed, so it counts even when the provider omits usage.
         else Usage(requests=1))
if (message is not None and first_choice is not None
        and first_choice.finish_reason == "content_filter"
        and not message.content and not message.refusal and not message.tool_calls):
    message.refusal = "Response withheld by the provider's content filter."
if tracing.include_data():
    span_generation.span_data.output = [message.model_dump()] if message is not None else []
```

**Flow:** `generation_span` + `model_span_errors` wrap the fetch → first choice/message extracted (empty choices tolerated) → usage synthesized with `requests=1` even when the provider omits usage (the request happened; tokens stay zero rather than the request vanishing) → a content-filter finish with an entirely empty message is promoted to a refusal so the turn is not silently empty, while real content under the same finish reason is kept verbatim → span output/usage populated only when `tracing.include_data()` → `provider_data = {"model", "response_id"}` threaded into `Converter.message_to_output_items(_normalize_any_llm_message(message), ...)` → logprobs converted and attached when present → raw usage snapshot only under `preserve_raw_usage is True`. `_normalize_any_llm_message` gates on assistant role (`ModelBehaviorError` otherwise), converts tool calls to OpenAI shapes, coerces non-string `reasoning_content` to "", and extracts `reasoning` only when `reasoning_content` is empty.
**Invariant:** a completed request always counts (`requests>=1`) even with no provider usage; a filtered empty turn surfaces as a refusal, never an empty output; real content is never replaced by a synthetic refusal; span population is data-policy-gated.
**Probe:** `tests/models/test_any_llm_model.py::test_any_llm_chat_path_surfaces_content_filter_refusal` (:594), `::test_any_llm_chat_path_content_filter_keeps_real_content` (:629).

## Streaming chat: span-before-yield and close discipline
**Path/Symbol:** `src/agents/extensions/models/any_llm_model.py:` `_stream_response_via_chat` (:707–795), `_populate_chat_generation_span` (:796–826).
**Signature:** `async def _stream_response_via_chat(...) -> AsyncGenerator[TResponseStreamEvent, None]`; `_populate_chat_generation_span(span_generation, final_response, tracing) -> None`.
**Data Shape:** chunks flow through `ChatCmplStreamHandler.handle_stream` over a normalized provider stream; usage dict zero-defaults detail objects (`{"cached_tokens": 0, "cache_write_tokens": 0}` / `{"reasoning_tokens": 0}`).

### Decisive source
```python
if chunk.type == "response.completed":
    final_response = chunk.response
    yielded_terminal_event = True
    self._populate_chat_generation_span(span_generation, final_response, tracing)
yield chunk
...
except asyncio.CancelledError:
    close_stream_in_background = True
    self._schedule_async_iterator_close(stream)
    raise
finally:
    if not close_stream_in_background:
        try:
            await self._close_stream_allowing_background_completion(stream)
        except Exception as exc:
            if yielded_terminal_event:
                log_model_action_debug(logger, "Ignoring stream cleanup error after terminal event", exc)
            else:
                raise
```

**Flow:** span is populated BEFORE yielding the terminal event, so a consumer that stops at `response.completed` still leaves a fully recorded span → `CancelledError` schedules a background iterator close and re-raises (never swallowed) → the `finally` closes the stream with the shield-and-detach helper; a cleanup error after a terminal event was yielded is logged and swallowed, before that it propagates → when the final response has no usage but requests were made, the span records `model_usage_to_span_usage(Usage(requests=1))` to stay aligned with the non-streaming path.
**Invariant:** cancellation always propagates; span recording never depends on consumer behavior past the terminal event; cleanup failures cannot mask a successful stream but can fail a stream that never completed.
**Probe:** `tests/models/test_any_llm_model.py` span-population tests (:2095 region pins span-before-yield; :1497+ close-discipline cases).

## History repair: one tool call per assistant message
**Path/Symbol:** `src/agents/extensions/models/any_llm_model.py:` `_fix_tool_message_ordering` (:1515–1611), applied at :885 before request conversion.
**Signature:** `def _fix_tool_message_ordering(self, messages: list[ChatCompletionMessageParam]) -> list[ChatCompletionMessageParam]`.
**Data Shape:** input may mix dicts and non-dict messages; only dict messages with `tool_calls` / `tool_call_id` participate; output preserves non-participating messages in place.

### Decisive source
```python
single_tool_msg = message_dict.copy()
single_tool_msg["tool_calls"] = [tool_call]
if split_idx > 0:
    for shared_field in ("content", "thinking_blocks", "reasoning_content", "reasoning"):
        single_tool_msg.pop(shared_field, None)
...
if tool_id in tool_call_messages and tool_id in tool_result_messages:
    fixed_messages.append(tool_call_message)
    fixed_messages.append(tool_result_message)   # call→result adjacency
```

**Flow:** index every assistant `tool_calls` message and every tool result by id → split each multi-call assistant message into one message per call, keeping content/thinking/reasoning fields only on the FIRST split (providers such as Anthropic reject duplicated signed thinking blocks) → re-emit messages so each tool call is immediately followed by its result; unpaired tool calls keep their split message, unpaired tool results pass through in place.
**Invariant:** no tool-call id is duplicated or dropped; signed thinking appears at most once per id; call→result adjacency is restored without reordering unrelated messages.
**Probe:** `tests/models/test_any_llm_model.py` ordering test (:1590 region pins first-split keeps shared fields, second split strips them, one call per message).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "_get_response_via_chat content_filter refusal _fix_tool_message_ordering", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt requests-count-even-without-usage, empty-filtered-turn→refusal, span-before-yield, and cancel-schedules-background-close. Adapt the shared-field strip list to whichever signed/reasoning fields your providers reject on duplication. Omit the logprobs attachment lane if your host does not surface logprobs. Coverage caveat: MCP not connected this pass; direct source+test reading at verified HEAD.
