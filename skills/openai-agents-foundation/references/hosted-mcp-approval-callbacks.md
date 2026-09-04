<!-- capsule-v2 -->
# Hosted MCP approval callbacks — how are auto-approved hosted MCP requests executed exactly once?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** When an MCP server supplies `on_approval_request`, what prevents double execution and where do rejection reasons travel?

## Callback execution + canonical identity guard
**Path/Symbol:** `src/agents/run_internal/tool_planning.py:` `execute_mcp_approval_requests` (:119–196), `_partition_mcp_approval_requests` (:576–590), `_apply_manual_mcp_approvals` (:843–861), `_append_mcp_callback_results` (:864–880).
**Signature:** `async def execute_mcp_approval_requests(*, agent, approval_requests, context_wrapper) -> list[RunItem]`.
**Data Shape:** each request wraps a raw `mcp_approval_request`; response raw item = `{approval_request_id, approve, type: "mcp_approval_response", reason?}`; partition criterion = callback present AND canonical invocation identity available.

### Decisive source
```python
if approval_status is None:
    invocation_status = context_wrapper._tool_invocation_status(request_item)
    if invocation_status is None:
        raise ModelBehaviorError("Hosted MCP approval requests require a canonical invocation identity.")
    if invocation_status[2]:
        raise ModelBehaviorError(
            "A Hosted MCP approval callback already ran, but its response was not "
            "committed. Start a new request instead of retrying the invocation.")
    context_wrapper._mark_tool_invocation_executed(request_item)
    ... callback ...
    approval_status = result["approve"]
    reason = result.get("reason", None)
```
Requests WITHOUT a callback (or without canonical identity) go to the manual bucket → they surface as `ToolApprovalItem` interruptions for the human loop instead. Caller copies `copy_tool_call_caller(request_item, raw_item)` so caller metadata propagates onto the response.

**Flow:** preflight dedup (see dedup-gate capsule) → partition callback vs manual → run callbacks concurrently (`gather_with_cancel`) → per request: check ledger status FIRST; mark executed BEFORE invoking; map `{approve, reason}` to approve/reject on the context wrapper; build response item with request id + optional reason string (non-str reasons dropped).

**Invariant:** Mark-executed precedes the callback so a crashing callback cannot be silently re-run later — recovery requires a NEW request; manual and callback paths are mutually exclusive per request; approvals recorded through the same wrapper API as function tools.

**Probe:** hosted-approval flows pinned in `tests/test_run_step_execution.py` and error scenarios in `tests/test_hitl_error_scenarios.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "execute mcp approval requests on_approval_request mark executed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt mark-before-run + loud uncommitted-recovery for any auto-approvable side effect; adapt the response-item shape to your MCP dialect; omit the manual bucket if your host always provides callbacks.
