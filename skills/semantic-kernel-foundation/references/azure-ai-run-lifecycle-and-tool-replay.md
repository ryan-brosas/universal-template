<!-- capsule-v2 -->
# Azure AI run lifecycle and tool replay — Assistant-family loop plus an MCP-approval branch and registered-tools validation

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does the Azure AI agent family drive a server-owned run to completion, and what does it add to the OpenAI Assistant loop it mirrors?

## AgentThreadActions.invoke (Azure AI)
**Path/Symbol:** `python/semantic_kernel/agents/azure_ai/agent_thread_actions.py:AgentThreadActions.invoke` (lines 109–460; status sets 103–104), `_poll_run_status`/`_poll_loop` (1089–1124), `_retrieve_message` (1128–1149), `_format_tool_outputs` (1239–1255), `_build_mcp_tool_approvals`/`_resolve_mcp_tool_approval` (1174–1236).
**Signature:** `async def invoke(cls, *, agent: "AzureAIAgent", thread_id: str, ..., polling_options: RunPollingOptions | None = None, function_choice_behavior: FunctionChoiceBehavior | None = None, **kwargs) -> AsyncIterable[tuple[bool, "ChatMessageContent"]]`.
**Data Shape:** Yields `(is_visible, ChatMessageContent)`. Same ClassVar sets as the OpenAI Assistant family: `polling_status = ["queued", "in_progress", "cancelling"]`, `error_message_states = ["failed", "cancelled", "expired", "incomplete"]`. `function_steps: dict[str, FunctionCallContent]` bridges tool-call ids to their `FunctionCallContent` for later result replay.

### Decisive source
```python
processed_step_ids = set()
function_steps: dict[str, FunctionCallContent] = {}

while run.status != "completed":
    run = await cls._poll_run_status(agent=agent, run=run, thread_id=thread_id,
                                     polling_options=polling_options or agent.polling_options)
    if run.status in cls.error_message_states:
        raise AgentInvokeException(f"Run failed with status: `{run.status}` ... "
                                   f"error: {error_message} and incomplete details reason: {...}")
    if run.status == "requires_action":
        if isinstance(run.required_action, SubmitToolOutputsAction):
            fccs = get_function_call_contents(run, function_steps)
            if fccs:
                yield False, generate_function_call_content(agent_name=agent.name, fccs=fccs)
                chat_history = ChatHistory() if kwargs.get("chat_history") is None else kwargs["chat_history"]
                _ = await cls._invoke_function_calls(kernel=kernel, fccs=fccs,
                                                     chat_history=chat_history, arguments=arguments,
                                                     function_choice_behavior=function_choice_behavior)
                tool_outputs = cls._format_tool_outputs(fccs, chat_history)
                await agent.client.agents.runs.submit_tool_outputs(run_id=run.id, thread_id=thread_id,
                                                                   tool_outputs=tool_outputs)
                continue
        elif isinstance(run.required_action, SubmitToolApprovalAction):
            tool_calls = run.required_action.submit_tool_approval.tool_calls
            if not tool_calls:
                await agent.client.agents.runs.cancel(run_id=run.id, thread_id=thread_id)
                continue
            mcp_tool_calls = [tc for tc in tool_calls if isinstance(tc, RequiredMcpToolCall)]
            if mcp_tool_calls:
                yield False, generate_mcp_call_content(agent_name=agent.name, mcp_tool_calls=mcp_tool_calls)
                tool_approvals = await cls._build_mcp_tool_approvals(...)
                await agent.client.agents.runs.submit_tool_outputs(run_id=run.id, thread_id=thread_id,
                                                                   tool_approvals=tool_approvals)
                continue
    # steps replay: tool_calls-first sort, processed_step_ids dedupe, per-tool-type match
    def sort_key(step):
        return (0 if step.type == "tool_calls" else 1, step.completed_at)
```

**Flow:** Create the run, then loop while status != "completed". Poll first (`_poll_run_status`
wraps `_poll_loop` in `asyncio.wait_for(..., run_polling_timeout)`; `_poll_loop` is sleep-first
with the shared `RunPollingOptions` ladder and retries anyway on retrieve failure). Error states
raise one exception folding `last_error.message` and `incomplete_details.reason`. The
`requires_action` gate has TWO branches: function-tool outputs (same shape as the OpenAI
Assistant family: fresh ChatHistory, one `asyncio.gather` of `kernel.invoke_function_call`,
id-keyed `str()` outputs, silent drop of results missing from history) and MCP tool APPROVAL
(empty tool_calls → cancel the run and continue; otherwise yield an invisible mcp-call message,
resolve each call through `_resolve_mcp_tool_approval`, submit `tool_approvals`). Otherwise the
run's steps are listed, filtered to completed-and-unprocessed, sorted tool_calls-first then by
`completed_at`, and replayed: code_interpreter is visible; FUNCTION results resolve through the
`function_steps` bridge; bing/azure_ai_search/file_search/openapi/MCP/deep_research tool calls
yield invisible content; message_creation retrieves the message and yields it visible. Every
processed step id lands in `processed_step_ids`.
**Invariant:** The loop is server-owned; the client only polls, submits outputs/approvals, and
replays steps exactly once (`processed_step_ids`). The MCP approval gate is FAIL-CLOSED: no
callback configured, callback exception, or a non-`True` result (strict `result is True`) all
deny the call, so an untrusted MCP server cannot execute without explicit opt-in. Unlike the
Assistant family, agent-defined `FunctionToolDefinition` tools are validated against the kernel
before the run starts (`_validate_function_tools_registered`, 1058–1086: any function tool name
missing from the kernel FQN set → `AgentInvokeException`).
**Probe:** `python/tests/unit/agents/azure_ai_agent/test_agent_thread_actions.py::test_agent_thread_actions_invoke` (line 89), `test_agent_thread_actions_invoke_with_requires_action` (148 — three yields: FunctionCallContent, FunctionResultContent, TextContent; `submit_tool_outputs.assert_awaited_once()`), `test_invoke_function_calls_blocks_disallowed_function` (526); `test_mcp_tool_approval.py` (dedicated fail-closed matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "AgentThreadActions invoke SubmitToolApprovalAction _build_mcp_tool_approvals processed_step_ids _format_tool_outputs", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the Assistant-shaped poll/error/replay loop, the two-branch requires-action gate, the
fail-closed MCP approval ladder (deny on missing callback, exception, or non-True), and the
pre-run registered-tools validation. Adapt the tool-call type match to your provider's tool
taxonomy. Omit the Azure SDK step/tool-call object specifics if your server streams events
instead of exposing step listing (see azure-ai-streaming-event-plane).
