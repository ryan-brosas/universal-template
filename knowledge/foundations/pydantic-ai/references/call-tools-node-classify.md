<!-- capsule-v2 -->
# CallToolsNode — the response-classification state machine that ends or continues a run

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter processes a model response in the agent loop, what is the exact decision ladder that classifies the response into tool-call / text-output / image-output / empty-retry and decides whether the run ends or issues a new model request?

## CallToolsNode._run_stream classification ladder
**Path/Symbol:** `pydantic_ai/_agent_graph.py:CallToolsNode` (1816-2288), `_run_stream` (1891-2063), `_handle_tool_calls` (2065-2172), `_handle_final_result` (2266-2286).
**Signature:** `CallToolsNode.run(ctx) -> ModelRequestNode | End[FinalResult]`; `_run_stream(ctx) -> AsyncIterator[HandleResponseEvent]`.
**Data Shape:** `model_response.parts` is a list of `TextPart | ToolCallPart | FilePart | NativeToolCallPart | NativeToolReturnPart | ThinkingPart | CompactionPart | SpeechPart`.

### Decisive source
```python
is_empty = not self.model_response.parts
is_thinking_only = not is_empty and all(isinstance(p, ThinkingPart) for p in self.model_response.parts)
if is_empty or is_thinking_only:
    if self.model_response.finish_reason == 'length':
        raise UnexpectedModelBehavior('Model token limit ... exceeded before any response was generated.')
    if is_empty and finish_reason == 'content_filter':
        raise ContentFilterError(...)
    if output_schema.allows_none:
        # empty/thinking-only is a VALID None result
        self._next_node = self._handle_final_result(ctx, FinalResult(result_data), [])
        return
    # else fall through to retry prompt

# part scan: text accumulates; ToolCallPart -> tool_calls; FilePart -> files;
# NativeToolCallPart resets text (thoughts); CompactionPart -> compaction_text;
# SpeechPart -> text

if tool_calls:
    response_output = (text, files) if ctx.deps.end_strategy == 'early' else None
    async for event in self._handle_tool_calls(ctx, tool_calls, response_output=response_output):
        yield event
    return
elif output_schema.allows_image and image := next((f for f in files if isinstance(f, BinaryImage)), None):
    self._next_node = await self._handle_image_response(ctx, image); return
elif text_processor := output_schema.text_processor:
    if text:
        self._next_node = await self._handle_text_response(ctx, text, text_processor); return
# else: build RetryPromptPart and raise ToolRetryError -> ModelRequestNode(retry)
```

**Flow:** (1) Empty/thinking-only responses: raise on `finish_reason='length'`; raise `ContentFilterError` on empty+content_filter; if `output_schema.allows_none`, treat as a valid `None` final result; else fall through to a retry prompt. (2) Scan parts into text/tool_calls/files/compaction_text. (3) If tool_calls present, `_handle_tool_calls` (under `end_strategy='early'` it may pre-empt tools if the response carries valid text/image output). (4) Else if image output allowed and an image present, handle image. (5) Else if a text processor exists and text present, handle text. (6) Else build a `RetryPromptPart('Please return text or call a tool.')` and raise `ToolRetryError`, which `consume_output_retry` converts into a `ModelRequestNode` retry (bounded by `max_output_retries`).
**Invariant:** Tool calls take precedence over text (a text+tool response executes the tools unless `end_strategy='early'`). `allows_none` makes empty a valid result (no forced retry). A `length` finish on an empty response is a hard error, never a retry. `_handle_final_result` appends the tool-return `ModelRequest` to history so the message history is reusable without dangling tool calls.
**Probe:** `tests/test_streaming.py` and `tests/test_agent.py` cover the empty/thinking-only/None-output and retry paths (e.g. `test_stream_output_type_union_data_before_kind` at :1882).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "CallToolsNode _run_stream ToolRetryError _handle_final_result", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the classification ladder (empty/None/length/content_filter → tool-call precedence → image → text → retry) and the `_handle_final_result` history-append; adapt the part classes and retry-prompt wording to your host; omit nothing — the tool-over-text precedence and length-is-hard-error rules are the portable invariants. Coverage clean.
