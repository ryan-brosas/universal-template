<!-- capsule-v2 -->
# Responses streaming item mapping — three-way event router: yield, buffer, or observer-only reasoning

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** In the Responses streaming loop, which events yield to the caller, which buffer for the tool round, and which route to the reasoning observer — and how do finished items become ChatMessageContent?

## invoke_stream event match ladder + item collectors
**Path/Symbol:** `python/semantic_kernel/agents/open_ai/responses_agent_thread_actions.py:invoke_stream` event match (lines 405–539), post-stream fold (541–590); `_build_streaming_msg` (697–716); `_create_output_item_done` (1025–1045); `_collect_items_from_output` (1075–1084); `_collect_text_and_annotations` (1101–1110); `_get_tool_calls_from_output` (892–910).
**Signature:** `_build_streaming_msg(*, agent, metadata, event, items, choice_index, role="assistant") -> StreamingChatMessageContent`; `_create_output_item_done(agent, response: ResponseOutputItem) -> ChatMessageContent`; `_collect_items_from_output(output: list) -> list`.
**Data Shape:** Three routing buckets per event: YIELD (ResponseTextDeltaEvent → StreamingTextContent), BUFFER (ResponseOutputItemAddedEvent tool calls + ResponseFunctionCallArgumentsDeltaEvent → FunctionCallContent into `all_messages`, never yielded), OBSERVE (all four reasoning events → on_intermediate_message callback only). `ResponseOutputItemDoneEvent` is the sole producer of finished `ChatMessageContent` into `output_messages`.

### Decisive source
```python
case ResponseTextDeltaEvent():
    text_content = StreamingTextContent(text=event.delta, choice_index=request_index)
    msg = cls._build_streaming_msg(agent=agent, metadata=metadata, event=event,
                                   items=[text_content], choice_index=request_index)
    yield msg                                   # ONLY delta event yielded to the caller
case ResponseOutputItemAddedEvent():
    function_calls = cls._get_tool_calls_from_output([event.item])
    if function_calls:
        function_call_returned = True           # latch: this stream needs a tool round
    msg = cls._build_streaming_msg(..., items=function_calls, ...)
    all_messages.append(msg)                    # buffered, NOT yielded
case ResponseOutputItemDoneEvent():
    msg = cls._create_output_item_done(agent, event.item)
    if output_messages is not None:
        output_messages.append(msg)             # finished message, appended not yielded
...
if not function_call_returned:
    return                                      # no tool calls → stream ends here
full_completion = reduce(lambda x, y: x + y, all_messages)   # fold buffered chunks
```

**Flow:** Every streaming message is assembled by `_build_streaming_msg` (inner_content=event, agent name/ai_model_id, choice_index=request_index). Text deltas stream out immediately; tool-call identity arrives on `ResponseOutputItemAddedEvent` (setting the `function_call_returned` latch) and its argument fragments arrive as `ResponseFunctionCallArgumentsDeltaEvent` chunks — both accumulate in `all_messages`. Reasoning deltas/done events (text + summary variants) build `StreamingReasoningContent`/`ReasoningContent` and go ONLY to `await on_intermediate_message(...)` — they never enter chat_history, all_messages, or output_messages (the observer-only rule pinned by the pass-10 reasoning capsule). After the stream: no tool call → return; otherwise fold `all_messages` with `reduce(x+y)` (StreamingChatMessageContent.__add__ guards make this safe within one model/choice), append to histories, gather tool executions, merge results via `_merge_streaming_function_results`, and continue the outer attempt loop. `_create_output_item_done` maps a finished `ResponseOutputMessage` through `_collect_items_from_output` → tool calls first, then `_collect_text_and_annotations` (ResponseOutputText → TextContent, each annotation → AnnotationContent via model_dump); role defaults to "assistant" when the item has none; status becomes `Status(response.status)` when present.
**Invariant:** Exactly one routing bucket per event type; tool-call fragments are never user-visible mid-stream (the caller sees text and, after the round, merged function results); `choice_index=request_index` ties every buffered chunk to its attempt so the fold cannot mix rounds. `_yield_function_result_messages` gates result yields on non-empty items.
**Probe:** `python/tests/unit/agents/openai_responses/test_openai_responses_thread_actions.py::test_invoke_stream_with_tool_calls` (line 427 — MockStream with ResponseOutputItemAddedEvent carrying ResponseFunctionToolCall + ResponseOutputItemDoneEvent; asserts exactly two final messages, first ASSISTANT), `test_invoke_stream_no_function_calls` (line 360 — no-tool stream path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "invoke_stream ResponseOutputItemAddedEvent ResponseFunctionCallArgumentsDeltaEvent _build_streaming_msg _create_output_item_done _collect_items_from_output", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the three-way event router (yield / buffer / observe) with a function_call_returned latch and reduce-fold per attempt for any SSE-driven tool-call stream. Adapt: the event-type dispatch table to your provider's event names; keep reasoning strictly observer-side if you port the intermediate-message callback. Omit: the annotation model_dump passthrough if your provider has no URL-citation annotations.
