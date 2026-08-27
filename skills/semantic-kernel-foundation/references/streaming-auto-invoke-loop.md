<!-- capsule-v2 -->
# Streaming auto-invoke loop — yield-while-loop, chunk folding via `__add__`, per-round result yield, silent exhaustion

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does the streaming twin of the bounded auto-invoke loop differ from the non-streaming loop in yield/merge ordering and termination?

## ChatCompletionClientBase.get_streaming_chat_message_contents streaming loop
**Path/Symbol:** `python/semantic_kernel/connectors/ai/chat_completion_client_base.py:ChatCompletionClientBase.get_streaming_chat_message_contents` (lines 196–318).
**Signature:** `async def get_streaming_chat_message_contents(self, chat_history: "ChatHistory", settings: "PromptExecutionSettings", **kwargs: Any) -> AsyncGenerator[list["StreamingChatMessageContent"], Any]`.
**Data Shape:** Same pre-loop setup as the non-streaming path (deepcopy settings at 218, cast to the service class at 220–221, kernel-required check at 230–234, `configure()` at 239–243). Loop counter is `request_index` over `range(settings.function_choice_behavior.maximum_auto_invoke_attempts)`; it is passed through to `_inner_get_streaming_chat_message_contents(chat_history, settings, request_index)` as `function_invoke_attempt` (base signature 60–76).

### Decisive source
```python
for request_index in range(settings.function_choice_behavior.maximum_auto_invoke_attempts):
    all_messages: list["StreamingChatMessageContent"] = []
    function_call_returned = False
    async for messages in self._inner_get_streaming_chat_message_contents(chat_history, settings, request_index):
        for msg in messages:
            if msg is not None:
                all_messages.append(msg)
                if not function_call_returned and any(isinstance(item, FunctionCallContent) for item in msg.items):
                    function_call_returned = True
        yield messages

    if not function_call_returned:
        return

    full_completion: StreamingChatMessageContent = reduce(lambda x, y: x + y, all_messages)
    function_calls = [item for item in full_completion.items if isinstance(item, FunctionCallContent)]
    chat_history.add_message(message=full_completion)
    ...
    results = await asyncio.gather(*[kernel.invoke_function_call(..., is_streaming=True, request_index=request_index, ...) for ...])
    ai_model_id = self._get_ai_model_id(settings)
    function_result_messages = merge_streaming_function_results(
        messages=chat_history.messages[-len(results):],
        ai_model_id=ai_model_id,
        function_invoke_attempt=request_index)
    if self._yield_function_result_messages(function_result_messages):
        yield function_result_messages

    if any(result.terminate for result in results if result is not None):
        break
```

**Flow:** Chunks are yielded to the caller as they arrive while `all_messages` accumulates them; a latch records whether any chunk carried a `FunctionCallContent`. When the inner stream ends without a tool call, the generator returns. Otherwise the chunks are folded into ONE completion with `reduce(lambda x, y: x + y, ...)` — `StreamingChatMessageContent.__add__` (`contents/streaming_chat_message_content.py` 171–206) raises `ContentAdditionException` on mismatched `choice_index` / `ai_model_id` / `encoding` / `role`, so the fold is only safe for one model's one choice. The folded message is added to history once per round; tool calls run in one `asyncio.gather` with `is_streaming=True`; the merged function-result message (see function-result-merge-rules) is yielded EVERY round regardless of terminate, gated by `_yield_function_result_messages` (non-empty list AND first message has items, 436–441); any `terminate=True` context breaks the loop. The whole loop runs inside `use_span(self._start_auto_function_invocation_activity(kernel, settings), end_on_exit=True)` (256).
**Invariant:** The loop is hard-bounded by `maximum_auto_invoke_attempts`; every round either returns (no tool call), breaks (terminate), or consumes exactly one attempt — and on exhaustion the generator simply ENDS: there is NO `for/else` tool-less final call, unlike the non-streaming loop (which resets function-choice settings and makes one final prose call, 171–174). The merged result carries `ai_model_id` (settings value or `self.ai_model_id` fallback, `_get_ai_model_id` 428–434) and `function_invoke_attempt=request_index` so downstream consumers can add two streaming messages together under the `__add__` identity guards.
**Probe:** `python/tests/unit/connectors/ai/open_ai/services/test_openai_chat_completion_base.py::test_scmc_run_out_of_auto_invoke_loop` (lines 910–960) and `test_scmc_terminate_through_filter` (1056–1111); request shape pinned by `test_scmc_function_choice_behavior` (722–776). Caveat: at this pin both count assertions are no-op expressions (`mock_create.call_count == 6` / `== 1` without `assert`) — exhaustion/terminate counts are pinned by comments only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "get_streaming_chat_message_contents function_call_returned merge_streaming_function_results", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: yield-as-you-go + accumulate-and-fold + per-round merged-result yield + terminate-break as the canonical streaming tool-loop shape; adopt the `__add__` identity guards (choice/model/encoding/role) as the precondition for folding chunks. Adapt the exhaustion policy deliberately — SK's streaming loop ends silently when the budget runs out while its non-streaming twin makes one final tool-less call; pick one and document it. Omit the attempt-index pass-through only if your stream identity model does not need to correlate result messages with rounds.
