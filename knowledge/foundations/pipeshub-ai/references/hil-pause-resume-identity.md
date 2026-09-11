<!-- capsule-v2 -->
# HIL pause→resume identity — how does a human-in-the-loop answer reach the right tool_use id after a restart?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** When an agent pauses for a human answer and the process dies, how do you rebuild a valid provider message on resume — which id goes in `tool_call_id`, and what must NOT be reused?

## Dual-id bridge: internal hil_request_id for lookup, ORIGINAL call.id for the ToolMessage
**Path/Symbol:** pause side `backend/python/app/agent_loop_lib/agent/observability.py` — `handle_clarify` (:250-299), `handle_tool_approval` (:197-247); resume side `backend/python/app/agent_loop_lib/agent/resume.py` — `resume()` (:19-90, HIL injection :46-53).
**Signature:** `async def handle_clarify(agent, call: ToolCall, goal, messages, turn_index) -> ToolResult`; resume: `async def resume(agent, checkpoint_id, hil_responses: dict[str,str] | None = None) -> AgentResult`.
**Data Shape:** `HILRequest(request_type=CLARIFICATION|TOOL_APPROVAL, run_id, session_id, question, context)` → store returns `request_id`. Resume input maps `hil_request_id → answer text`; injected message is `ToolMessage(content=json.dumps({"approved": True, "answer": answer}), tool_call_id=<original call.id>)`.

### Decisive source
```python
# resume(): the whole trick in four lines
    if hil_responses and checkpoint.hil_request_id:
        answer = hil_responses.get(checkpoint.hil_request_id, "")
        tool_call_id = checkpoint.pending_tool_call_id or checkpoint.hil_request_id
        hil_msg = ToolMessage(
            content=json.dumps({"approved": True, "answer": answer}),
            tool_call_id=tool_call_id,
        )
```

**Flow:** model calls clarify/approval-gated tool → handler submits `HILRequest` to `hil_store`, stamps a `hil_pause` checkpoint carrying BOTH ids (`hil_request_id=request_id` for lookup, `pending_tool_call_id=call.id` for provider validity), emits TOOL_CALL with both ids, blocks on `wait_for_response` (clarify converts the response into its own ToolResult; approval returns just the bool). On resume: load checkpoint → replay messages into a fresh ContextManager → look up the answer BY hil_request_id → address the ToolMessage TO pending_tool_call_id (fallback: hil_request_id if the older field is absent).
**Invariant:** (1) The two ids are NEVER interchangeable: hil_request_id routes human answers; tool_call_id satisfies the provider's `tool_result.tool_use_id` must-match-the-assistant-tool_use-block rule. (2) The paused turn's assistant response (the tool_use block itself) is already inside `checkpoint.messages` — once the HIL ToolMessage is injected, that turn counts complete. (3) Approval fallback when no hil_store configured is deny-by-default (`return False`) — "nothing to ask, so don't allow it". (4) Clarify with no store returns an error ToolResult rather than pausing.
**Probe:** `backend/python/tests/unit/agent_loop_lib/agent/test_handle_tool_approval.py` (approval pause path). Coverage caveat: the crash-mid-wait→resume leg has NO direct test — verified by source reading of both sides plus the dual-id comments at base.py:46-50 and observability.py:231-233/280-282.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "handle_clarify handle_tool_approval hil_store wait_for_response hil_request_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-id bridge and the pause-checkpoint-before-blocking order; adapt HIL request schema, store backend, and the `{approved, answer}` payload shape to host; omit the legacy single-id fallback (`or checkpoint.hil_request_id`) only if your checkpoints are guaranteed new-format. Coverage caveat: cross-restart resume leg untested directly — source-grounded only.
