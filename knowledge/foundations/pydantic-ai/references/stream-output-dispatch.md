<!-- capsule-v2 -->
# validate_response_output — the streaming output-type dispatch ladder

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter validates a streamed model response into structured output, how does it dispatch among tool-call output, deferred-tool requests, image output, and text output, and how do `allow_partial`/`wrap_validation_errors` propagate?

## AgentStream.validate_response_output dispatch
**Path/Symbol:** `pydantic_ai/result.py:AgentStream.validate_response_output` (244-308).
**Signature:** `validate_response_output(message, *, allow_partial=False) -> OutputDataT`.
**Data Shape:** `final_result_event` (with `.tool_name`) tells which tool produced the output; `message.tool_calls` carries the tool-call parts.

### Decisive source
```python
final_result_event = self._raw_stream_response.final_result_event
if final_result_event is None:
    raise UnexpectedModelBehavior('Invalid response, unable to find output')
output_tool_name = final_result_event.tool_name
if self._output_schema.toolset and output_tool_name is not None:
    tool_call = next((p for p in message.tool_calls if p.tool_name == output_tool_name), None)
    if tool_call is None:
        raise UnexpectedModelBehavior(f'Invalid response, unable to find tool call for {output_tool_name!r}')
    return await self._tool_manager.handle_output_tool_call(
        tool_call, schema=self._output_schema, allow_partial=allow_partial, wrap_validation_errors=False)
elif deferred_tool_requests := _get_deferred_tool_requests(message.tool_calls, self._tool_manager):
    if not self._output_schema.allows_deferred_tools:
        raise UserError('A deferred tool call was present, but DeferredToolRequests is not among output types...')
    return cast(OutputDataT, deferred_tool_requests)
elif self._output_schema.allows_image and message.images:
    return await self._validate_image_output(message.images[0], allow_partial=allow_partial)
elif text_processor := self._output_schema.text_processor:
    # accumulate TextPart content; NativeToolCallPart resets text
    run_ctx = replace(self._run_ctx, partial_output=allow_partial)
    return await run_output_with_hooks(text_processor, text=text, run_context=run_ctx,
        capability=self._root_capability, schema=self._output_schema,
        allow_partial=allow_partial, wrap_validation_errors=False, output_validators=self._output_validators)
else:
    raise UnexpectedModelBehavior('Invalid response, unable to process text output')
```

**Flow:** Dispatch order: (1) tool-call output (the output tool named by `final_result_event`) → `handle_output_tool_call`; (2) deferred tool requests (if allowed by the schema, else `UserError`); (3) image output; (4) text output via `run_output_with_hooks`. All paths pass `allow_partial` through and use `wrap_validation_errors=False` (streaming — errors propagate as-is rather than being wrapped into retry prompts). The outer `except (ValidationError, ModelRetry)` re-raises on partial, but on non-partial converts to `UnexpectedModelBehavior` ("retries are not supported in run_stream()").
**Invariant:** Dispatch order is tool-call → deferred → image → text. `wrap_validation_errors=False` in streaming (no retry prompts mid-stream); `allow_partial` propagates to every branch. A deferred tool call when `DeferredToolRequests` isn't an allowed output type is a `UserError`, not a silent pass.
**Probe:** `tests/test_streaming.py` covers the output-type dispatch (e.g. `test_invalid_output_tool_args_stream_output` at :2178, `test_stream_output_type_union_data_before_kind` at :1882).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "validate_response_output final_result_event handle_output_tool_call", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tool→deferred→image→text dispatch and the `wrap_validation_errors=False` streaming rule; adapt the output-schema flags to your host; omit nothing — the dispatch order and no-retry-in-stream invariant are portable. Coverage clean.
