<!-- capsule-v2 -->
# Azure AI streaming event plane — event-driven stream where tool-output submission swaps the stream itself

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does an event-driven agent stream execute tools mid-stream and still deliver the final assistant messages?

## AgentThreadActions.invoke_stream / _process_stream_events (Azure AI)
**Path/Symbol:** `python/semantic_kernel/agents/azure_ai/agent_thread_actions.py:AgentThreadActions.invoke_stream` (lines 463–580), `_process_stream_events` (582–812), `_handle_streaming_requires_action` (1258–1293).
**Signature:** `async def invoke_stream(cls, *, agent, thread_id, ..., output_messages: list[ChatMessageContent] | None = None, function_choice_behavior: FunctionChoiceBehavior | None = None, **kwargs) -> AsyncIterable["StreamingChatMessageContent"]`; `_process_stream_events(stream: AsyncAgentRunStream, ..., function_steps: dict, active_messages: dict[str, RunStep], ...)`.
**Data Shape:** Yields only visible streaming deltas. `output_messages` is the caller-owned accumulator that receives function-call/result contents and the final retrieved messages. `active_messages: dict[msg_id, RunStep]` records message-creation steps completed mid-stream for end-of-run retrieval. `THREAD_MESSAGE_ID` metadata key threads the current thread-message id onto tool-call contents.

### Decisive source
```python
elif event_type == AgentStreamEvent.THREAD_RUN_REQUIRES_ACTION:
    run = cast(ThreadRun, event_data)
    if isinstance(run.required_action, SubmitToolOutputsAction):
        action_result = await cls._handle_streaming_requires_action(
            agent_name=agent.name, kernel=kernel, run=run, function_steps=function_steps,
            arguments=arguments, function_choice_behavior=function_choice_behavior)
        if action_result is None:
            raise RuntimeError(f"Function call required but no function steps found ...")
        for content in (action_result.function_call_streaming_content,
                        action_result.function_result_streaming_content):
            if content and output_messages is not None:
                if thread_msg_id and THREAD_MESSAGE_ID not in content.metadata:
                    content.metadata[THREAD_MESSAGE_ID] = thread_msg_id
                output_messages.append(content)          # accumulated, NOT yielded
        handler: BaseAsyncAgentEventHandler = AsyncAgentEventHandler()
        await agent.client.agents.runs.submit_tool_outputs_stream(
            run_id=run.id, thread_id=thread_id,
            tool_outputs=action_result.tool_outputs, event_handler=handler)
        stream = handler                                  # the handler IS the new stream
        break                                             # re-enter the while True loop
...
elif event_type == AgentStreamEvent.THREAD_RUN_COMPLETED:
    if active_messages:
        for msg_id, step in active_messages.items():
            message = await cls._retrieve_message(agent=agent, thread_id=thread_id, message_id=msg_id)
            if message and hasattr(message, "content"):
                final_content = generate_message_content(agent.name, message, step)
                if output_messages is not None:
                    output_messages.append(final_content)
    return
```

**Flow:** `invoke_stream` validates the FCB gate, assembles tools, merges instructions, opens
`runs.stream`, and delegates to `_process_stream_events`. The event loop is a `while True` over
an `async for event_type, event_data, _ in stream_iter`: THREAD_MESSAGE_DELTA yields every delta;
THREAD_RUN_STEP_DELTA matches each tool-call type (code_interpreter visible; bing/azure_search/
file_search/openapi/MCP/deep_research accumulated invisibly) and stamps `THREAD_MESSAGE_ID` into
metadata; THREAD_RUN_REQUIRES_ACTION executes the tools (`_handle_streaming_requires_action`:
fccs → streaming function-call content → one gather over a fresh ChatHistory → the OpenAI
Assistant `merge_streaming_function_results(messages=chat_history.messages[-len(results):],
name=agent_name)` twin → `_format_tool_outputs`), pushes the call/result contents into
`output_messages`, submits outputs THROUGH A STREAM (`submit_tool_outputs_stream` with a fresh
`AsyncAgentEventHandler`), then swaps `stream = handler` and `break`s so the outer `while True`
re-enters iterating the handler's events; THREAD_RUN_COMPLETED replays `active_messages` through
`_retrieve_message` into `output_messages` and returns; THREAD_RUN_FAILED raises `RuntimeError`.
The stream adapter is duck-typed: `async with` is used only when the stream supports context
management (tool-output handlers support iteration only).
**Invariant:** The caller sees a continuous visible-delta stream across the tool round: the
handoff between the model stream and the tool-output event stream is invisible because the
submission itself returns the continuation stream. Function-call/result contents are never
yielded — they travel only through `output_messages` (the same contract as the OpenAI Assistant
family's `on_intermediate_message`). Final assistant messages are NOT folded from chunks (no
`__add__` reduce like the kernel/Responses loops); they are re-retrieved from the server at
THREAD_RUN_COMPLETED using `active_messages`.
**Probe:** `python/tests/unit/agents/azure_ai_agent/test_agent_thread_actions.py::test_agent_thread_actions_invoke_stream` (line 336 — MockStream event list through the full plane), `test_invoke_stream_raises_for_non_auto_fcb` (644), plus `test_agent_thread_actions_invoke_with_requires_action` (148) for the non-streaming twin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "AgentThreadActions _process_stream_events submit_tool_outputs_stream AsyncAgentEventHandler active_messages THREAD_RUN_COMPLETED", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the stream-swap pattern (submit-through-stream, then iterate the handler as the new
stream), the output_messages-only channel for intermediate tool contents, and end-of-run server
retrieval instead of client-side chunk folding. Adapt the event-name taxonomy to your provider.
Omit the duck-typed context-manager guard if your streams are always async-iterables.
