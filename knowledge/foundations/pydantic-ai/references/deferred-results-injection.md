<!-- capsule-v2 -->
# Deferred tool-results injection — delivering human/tool results into history without double execution

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a host supplies results for previously-deferred tool calls (approvals, external executions), how are they spliced in, and which calls must never be overridden?

## UserPromptNode._handle_deferred_tool_results
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_agent_graph.py:UserPromptNode._handle_deferred_tool_results` (660-705).
**Signature:** `async _handle_deferred_tool_results(deferred_tool_results: DeferredToolResults, messages, ctx) -> CallToolsNode`.
**Data Shape:** `tool_call_results: dict[str, DeferredToolResult | Literal['skip']]`; scans history backwards for the last `ModelResponse` and its following `ModelRequest`.

### Decisive source
```python
if not messages: raise UserError('Tool call results were provided, but the message history is empty.')
# reverse scan: LAST response with open calls + the request that follows it
for message in reversed(messages):
    if isinstance(message, ModelRequest): last_model_request = message
    elif isinstance(message, ModelResponse):
        last_model_response = message; break
if not last_model_response: raise UserError('...does not contain a ModelResponse.')
if not last_model_response.tool_calls: raise UserError('...unprocessed tool calls.')

tool_call_results = dict(deferred_tool_results.to_tool_call_results())
if last_model_request:
    for part in last_model_request.parts:
        if isinstance(part, ToolReturnPart | RetryPromptPart):
            if part.tool_call_id in tool_call_results:
                raise UserError(f'Tool call {part.tool_call_id!r} was already executed '
                                'and its result cannot be overridden.')
            tool_call_results[part.tool_call_id] = 'skip'   # settled => sentinel

return CallToolsNode(last_model_response,
                     tool_call_results=tool_call_results,
                     tool_call_metadata=deferred_tool_results.metadata or None,
                     user_prompt=self.user_prompt)          # prompt rides along to CallToolsNode
```

**Flow:** validate history shape → collect user-supplied results → mark already-executed sibling calls `'skip'` → skip ModelRequestNode entirely and enter CallToolsNode with the results map (+optional metadata, +the run's user_prompt so it lands after the tool results).
**Invariant:** Overriding an already-executed call is a loud `UserError`, not a silent replace — idempotency of resume is protected at the door. Settled calls get the `'skip'` sentinel rather than being dropped, so CallToolsNode sees a total map over the response's calls. The deferred path never builds a ModelRequestNode.
**Probe:** `tests/test_agent.py::test_user_prompt_with_deferred_tool_results` (11021) pins results+user_prompt co-delivery; `test_deferred_tool_results_reject_duplicate_tool_call_ids_in_history` (10989) pins the override-is-error rule; error-shape tests at 10868.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_handle_deferred_tool_results to_tool_call_results skip sentinel CallToolsNode", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the override-is-error guard and the `'skip'` sentinel for settled calls; adapt the reverse-scan to your history classes; omit the metadata sideband if your host has no per-result metadata. Complements `resume-path.md` (which covers the approval-side variants). Coverage clean.
