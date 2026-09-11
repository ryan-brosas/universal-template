<!-- capsule-v2 -->
# Auto-invoke loop bounds — attempts budget, parallel gather, terminate short-circuit, tool-less final call

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How do you bound a model-driven tool-calling loop so it cannot spin forever, while still allowing parallel tool calls and an early exit?

## ChatCompletionClientBase.get_chat_message_contents auto-invoke loop
**Path/Symbol:** `python/semantic_kernel/connectors/ai/chat_completion_client_base.py:ChatCompletionClientBase.get_chat_message_contents` (lines 85–174).
**Signature:** `async def get_chat_message_contents(self, chat_history: "ChatHistory", settings: "PromptExecutionSettings", **kwargs: Any) -> list["ChatMessageContent"]`.
**Data Shape:** Loop counter is `request_index` over `range(settings.function_choice_behavior.maximum_auto_invoke_attempts)`; per round, `function_calls` are the `FunctionCallContent` items of `completions[0]`; each gathered result is an `AutoFunctionInvocationContext | None` carrying `terminate`.

### Decisive source
```python
for request_index in range(settings.function_choice_behavior.maximum_auto_invoke_attempts):
    completions = await self._inner_get_chat_message_contents(chat_history, settings)
    function_calls = [item for item in completions[0].items if isinstance(item, FunctionCallContent)]
    if (fc_count := len(function_calls)) == 0:
        return completions
    chat_history.add_message(message=completions[0])
    results = await asyncio.gather(*[
        kernel.invoke_function_call(function_call=fc, chat_history=chat_history, ...)
        for fc in function_calls])
    if any(result.terminate for result in results if result is not None):
        return merge_function_results(chat_history.messages[-len(results):])
else:
    # Do a final call, without function calling when the max has been reached.
    self._reset_function_choice_settings(settings)
    return await self._inner_get_chat_message_contents(chat_history, settings)
```

**Flow:** Settings are deep-copied before mutation (107) and converted to the service's own settings class (109–110). Rounds: LLM call → zero tool calls means done; otherwise the assistant tool-call message is appended once, all tool calls run concurrently in one `asyncio.gather`, and any context with `terminate=True` returns immediately with the last N history messages merged. If the attempt budget exhausts without terminate, Python's `for/else` executes one final LLM call with function-choice settings reset — the model answers in prose because no tools are offered.
**Invariant:** The loop is hard-bounded by `maximum_auto_invoke_attempts`; every round either returns, terminates, or consumes exactly one attempt, and the last round can never request more tools.
**Probe:** `python/tests/unit/connectors/ai/open_ai/services/test_openai_chat_completion_base.py::test_cmc_run_out_of_auto_invoke_loop` (lines 465–505) pins exhaustion behavior; parallel-tool-call shape pinned by `test_azure_chat_completion.py::test_cmc_tool_calling_parallel_tool_calls` (617–688).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "maximum_auto_invoke_attempts merge_function_results terminate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: attempts budget + per-round gather + terminate short-circuit + for/else tool-less finale as the canonical bounded agent-tool-loop skeleton. Adapt where terminate originates (SK sets it from auto-function-invocation filters, e.g. human-in-the-loop or single-shot policies) and how merged results are projected onto your message model. Omit the settings deep-copy only if your settings objects are already immutable per call.
