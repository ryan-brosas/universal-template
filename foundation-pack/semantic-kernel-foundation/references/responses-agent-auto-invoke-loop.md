<!-- capsule-v2 -->
# Responses agent auto-invoke loop — kernel loop transplanted client-side, for/else finale non-streaming only

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does the Responses agent run its own bounded tool loop, and does the kernel's streaming/non-streaming exhaustion asymmetry survive the transplant?

## ResponsesAgentThreadActions.invoke / invoke_stream
**Path/Symbol:** `python/semantic_kernel/agents/open_ai/responses_agent_thread_actions.py:ResponsesAgentThreadActions.invoke` (87–288; status sets 81–82), `invoke_stream` (289–596), `_poll_until_completed` (640–653).
**Signature:** `async def invoke(cls, *, agent, chat_history, thread, store_enabled: bool, function_choice_behavior: "FunctionChoiceBehavior", arguments=None, ...) -> AsyncIterable[tuple[bool, "ChatMessageContent"]]`.
**Data Shape:** Yields `(is_visible, ChatMessageContent)`; visibility tuple is `intermediate=False / final=True`. Error set is narrower than the Assistant family: `error_message_states = ["failed", "incomplete"]` (no cancelled/expired — the Responses API has no such run states). Loop bound comes from `function_choice_behavior.maximum_auto_invoke_attempts`.

### Decisive source
```python
override_history = chat_history
if not store_enabled:
    override_history = ChatHistory(messages=[*thread._chat_history.messages, *chat_history.messages])
previous_response_id = None
if thread.store_enabled and thread.response_id:
    previous_response_id = thread.response_id

for request_index in range(function_choice_behavior.maximum_auto_invoke_attempts):
    response = await cls._get_response(..., previous_response_id=previous_response_id, ...)
    if store_enabled:
        thread.response_id = response.id
        previous_response_id = response.id          # chain tool outputs to the right response
    if response.status in cls.error_message_states:
        raise AgentInvokeException(f"Run failed with status: `{response.status}` ...")
    response = await asyncio.wait_for(cls._poll_until_completed(agent, response, ...),
                                      timeout=agent.polling_options.run_polling_timeout.total_seconds())
    reasoning_items = cls._get_reasoning_items_from_output(response.output)
    if reasoning_items:
        yield False, reasoning_message               # intermediate, not visible
    function_calls = cls._get_tool_calls_from_output(response.output)
    if (fc_count := len(function_calls)) == 0:
        yield True, cls._create_response_message_content(response, ...)
        break
    ...
    results = await asyncio.gather(*[kernel.invoke_function_call(..., request_index=request_index, ...)
                                     for function_call in function_calls])
    terminate_flag = any(result.terminate for result in results if result is not None)
    for msg in merge_function_results(override_history.messages[-len(results):]):
        yield terminate_flag, msg
else:
    # Do a final call, without function calling when the max has been reached.
    function_choice_behavior = FunctionChoiceBehavior.NoneInvoke()
    response = await cls._get_response(...)
    yield True, cls._create_response_message_content(response, ...)
```

**Flow:** Non-streaming: a `for` loop over `maximum_auto_invoke_attempts` rounds. Each round gets
a response (chained via `previous_response_id` when storing; otherwise the thread history is
merged once into `override_history` up front), raises on error status, polls until completed
(sleep-first retrieve loop with NO internal timeout — the caller's `wait_for` owns it), yields
reasoning items as intermediate messages, breaks with a final visible message when there are no
tool calls, otherwise gathers tool invocations and yields the merged results stamped with the
terminate flag. Exhaustion falls into `for/else`: one final call with
`FunctionChoiceBehavior.NoneInvoke()` and a visible final message. Streaming: same bound and
round shape, but chunks are yielded as they arrive (text deltas only), accumulated in
`all_messages`, latched by `function_call_returned`, folded with `reduce(lambda x, y: x + y, ...)`
when tool calls arrived, invoked with `is_streaming=True`, merged via
`_merge_streaming_function_results` (stamped with ai_model_id + function_invoke_attempt), yielded
through the `_yield_function_result_messages` gate, and terminate breaks. On no-tool-call the
stream simply returns — there is NO `for/else` finale in streaming.
**Invariant:** The kernel-core exhaustion asymmetry is preserved in the transplant: non-streaming
ends with a tool-less `NoneInvoke` finale; streaming ends silently. `previous_response_id`
chaining is what associates submitted tool outputs with the right stored response; without
`store_enabled` the loop must carry full history itself (`override_history`).
**Probe:** `python/tests/unit/agents/openai_responses/test_openai_responses_thread_actions.py::test_invoke_reaches_maximum_attempts` (118–174: 3 tool responses + 1 final = 4 `_get_response` calls with `maximum_auto_invoke_attempts=3` — pins the for/else finale), `test_invoke_with_function_calls` (175–227: exactly 3 messages), `test_invoke_no_function_calls` (72–92), `test_invoke_raises_on_failed_response` (93–117), `test_invoke_stream_no_function_calls` (360–426), `test_invoke_stream_with_tool_calls` (427–500).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "ResponsesAgentThreadActions invoke previous_response_id NoneInvoke _poll_until_completed", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the bounded client-side loop with per-round error gate, poll-until-completed, reasoning-as-intermediate yield, and the for/else NoneInvoke finale for non-streaming. Adopt the asymmetry consciously: pick one exhaustion policy per transport mode and document it. Adapt the store/chaining model to your provider (previous_response_id is Responses-specific). Omit reasoning-item extraction if your provider has no reasoning output type.
