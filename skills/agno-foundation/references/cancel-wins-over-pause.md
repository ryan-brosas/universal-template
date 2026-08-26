<!-- capsule-v2 -->
# Cancel wins over pause — Why must cancelling a paused run clear its pause flags before persisting?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What happens to half-paused HITL tool state when the run is cancelled instead of resumed?

## The cancellation handler strips unresolved requirements and zeroes pause flags
**Path/Symbol:** `libs/agno/agno/agent/_run.py:_handle_run_cancellation` (:5653-5694).
**Signature:** `_handle_run_cancellation(run_response, error: Union[RunCancelledException, KeyboardInterrupt], run_messages: Optional[RunMessages]) -> RunOutput`.
**Data Shape:** mutates run_response: status=cancelled, content fallback to reason, messages preserved (only `add_to_agent_memory` ones), metrics timer stopped.

### Decisive source
```python
# Clear pause state so cancel wins over a paused HITL run
if run_response.requirements:
    run_response.requirements = [req for req in run_response.requirements if req.is_resolved()]
if run_response.tools:
    for tool in run_response.tools:
        if tool.is_paused:
            tool.requires_confirmation = False
            tool.requires_user_input = False
            tool.external_execution_required = False
```

**Flow:** normalize reason (`RunCancelledException` str else "Operation cancelled by user" for KeyboardInterrupt) → set status → preserve partial streamed content by folding it into the trailing empty assistant message or appending a fresh one → stop timer → drop UNRESOLVED requirements → clear all three pause flags on paused tools → caller persists via cleanup_and_store (or `_persist_cancelled_run_in_background` on client disconnect).
**Invariant:** If a persisted cancelled row kept requires_confirmation=True / external_execution_required=True, a later continue/resume would see a pending pause and re-enter HITL flow for a dead run — cancel must be terminal. Partial content preservation means the user's half-received answer is not lost in history.
**Probe:** `sed -n '5643,5695p' libs/agno/agno/agent/_run.py | grep -c '= False'` → **3** (the three flag clears); direct behavior tests `libs/agno/tests/integration/agent/test_agent_run_cancellation.py::test_continue_session_after_cancelled_agent_run` and `::test_cancel_agent_sync_streaming_preserves_content_in_db`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "_handle_run_cancellation clear pause state", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the terminal-cancel invariant (strip unresolved pauses before persisting any cancelled state); adapt reason strings/messages policy; omit partial-content folding if your transport never streams partial answers into storage.
