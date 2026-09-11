<!-- capsule-v2 -->
# Pause handler stamps approvals then stores — What exactly happens when the model requests a tool that needs human action?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What is the pause exit sequence, and why do background futures get joined BEFORE persisting?

## Pause = status flip + content fallback + approval stamping + store, then return to caller
**Path/Symbol:** `libs/agno/agno/agent/_run.py:handle_agent_run_paused` (:209-230); stream variant (:233-270); async twins (:273-337). Trigger at :574-591 inside `_run`.
**Signature:** `handle_agent_run_paused(agent, run_response, session, user_id=None, run_context=None) -> RunOutput`.
**Data Shape:** mutates run_response (status/content/events); returns it for the caller to drive resume.

### Decisive source
```python
# In _run, right after update_run_response:
if any(tool_call.is_paused for tool_call in run_response.tools or []):
    wait_for_open_threads(
        memory_future=memory_future,
        cultural_knowledge_future=cultural_knowledge_future,
        learning_future=learning_future,
    )
    merge_background_metrics(run_response.metrics,
        collect_background_metrics(memory_future, cultural_knowledge_future, learning_future))
    return handle_agent_run_paused(...)

def handle_agent_run_paused(agent, run_response, session, ...):
    run_response.status = RunStatus.paused
    if not run_response.content:
        run_response.content = get_paused_content(run_response)
    # Stamp approval_id on tools before storing so the DB has the complete data.
    create_approval_from_pause(db=agent.db, ...)
    cleanup_and_store(agent, run_response=run_response, session=session, ...)
```

**Flow:** tool execution sets `is_paused` on ToolExecutions needing confirmation/user-input/user-feedback/external-execution → run loop detects ANY paused tool AFTER the model response → joins background memory/learning/culture threads FIRST (a paused run may sit paused for hours; those threads must not dangle) → merges their metrics → flips status → synthesizes human-readable content via `get_paused_content` when empty (skipping `external_execution_silent` tools, utils/response.py:129+) → stamps approval ids → persists → yields RunPausedEvent (stream variant, BEFORE storage per event contract) → returns control to caller.
**Invariant:** The persisted paused row must be self-contained: metrics merged, approvals stamped, content present — because resumption may happen in a different process against only the DB row. Pause is an EXIT, not an internal wait state.
**Probe:** `grep -n 'create_approval_from_pause' libs/agno/agno/agent/_run.py | wc -l` → **4** (one per pause-handler variant); direct behavior tests `libs/agno/tests/unit/run/test_approval.py::TestGetPauseType::test_user_input_takes_precedence` (pause-type priority feedback > external > input > confirmation) + `libs/agno/tests/unit/team/test_acontinue_run_background_stream.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "handle_agent_run_paused create_approval_from_pause RunPausedEvent", limit: 10, fields: ["signature", "name", "file"] });
```
(resolves acreate_approval_from_pause line-exact 209-271.)

## Verdict
Adopt "join side-effects then persist self-contained paused rows" as the pause contract; adapt pause-type taxonomy wording; omit silent-external tools if you always surface pauses.
