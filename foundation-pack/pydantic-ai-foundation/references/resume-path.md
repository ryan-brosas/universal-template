<!-- capsule-v2 -->
# Resume path — how does a fresh run with DeferredToolResults splice results into history without double-executing?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** When the host resumes with `deferred_tool_results=`, how are results matched to the original response's calls, and which history parts mark calls as already-handled?

## UserPromptNode._handle_deferred_tool_results
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_agent_graph.py:UserPromptNode._handle_deferred_tool_results` (660–708), entry guard at :543-544; consumption in `_tool_execution.py:_ToolCallProcessor.__post_init__` resume branch (390–426).
**Signature:** `_handle_deferred_tool_results(deferred_tool_results: DeferredToolResults, messages, ctx) -> CallToolsNode` — skips `ModelRequestNode` entirely and re-enters at `CallToolsNode(last_model_response, tool_call_results=..., tool_call_metadata=...)`.
**Data Shape:** Internal map is `dict[str, DeferredToolResult | Literal['skip']]`; `'skip'` marks calls already settled in the original step; metadata rides separately keyed by id.

### Decisive source
```python
# _agent_graph.py:668-705 (condensed to the invariants)
for message in reversed(messages):                 # find LAST ModelResponse
    if isinstance(message, _messages.ModelResponse):
        last_model_response = message; break

tool_call_results.update(deferred_tool_results.to_tool_call_results())

if last_model_request:
    for part in last_model_request.parts:
        if isinstance(part, _messages.ToolReturnPart | _messages.RetryPromptPart):
            if part.tool_call_id in tool_call_results:
                raise exceptions.UserError(
                    f'Tool call {part.tool_call_id!r} was already executed and its result cannot be overridden.')
            tool_call_results[part.tool_call_id] = 'skip'

# Skip ModelRequestNode and go directly to CallToolsNode
return CallToolsNode(..., tool_call_results=tool_call_results,
                     tool_call_metadata=deferred_tool_results.metadata or None, ...)
```

**Flow:** Guard fires only when `deferred_tool_results` was passed → walk history backwards for the last ModelResponse (must exist, must have unprocessed tool calls, else `UserError`) → normalize loose results → scan the trailing ModelRequest: any ToolReturn/Retry part with an id present in BOTH places is a double-settle error; ids settled in the original step become `'skip'` → construct CallToolsNode directly. Downstream, the processor requires every eligible call (function/unknown/external/unapproved) to have a supplied result or skip, enforces `eligible ⊆ provided ⊆ response-calls`, rejects duplicate ids (ambiguous binding), and drops `'skip'` entries from what actually executes.
**Invariant:** A settled call can NEVER be overridden — fail closed rather than silently mis-bind. The `'skip'` sentinel is what lets one resume cover a response whose calls partially completed before pausing. Resume executes deferred kinds through the regular pipeline (so events, hooks, retry budgets all behave identically to first-pass execution).
**Probe:** `tests/test_agent.py::test_agent_run_id_fresh_on_deferred_resume` (:4052) + surrounding resume tests pin run-id freshness and result application.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_handle_deferred_tool_results tool_call_results skip deferred", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the backwards-history scan + override-is-an-error + 'skip'-sentinel design; adapt to your persistence format if you don't keep full message history; omit the graph-node plumbing (CallToolsNode construction) for a non-graph executor. Caveat: none — read at HEAD this session.
