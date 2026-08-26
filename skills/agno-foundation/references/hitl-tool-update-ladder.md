<!-- capsule-v2 -->
# HITL tool update ladder — How does the resume dispatch route each paused tool kind back into execution?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** When a paused run continues, which branch executes which pause kind, and what flags flip?

## One four-case ladder serves confirm / external / agentic-input / user-input
**Path/Symbol:** `libs/agno/agno/agent/_tools.py:handle_tool_call_updates` (:905-951); stream twin :953-1004; async twins :1007-1106.
**Signature:** `handle_tool_call_updates(agent, run_response, run_messages, tools: List[Union[Function, dict]])`.
**Data Shape:** iterates `run_response.tools` (ToolExecution records); `_functions` maps name→Function for lookup.

### Decisive source
```python
for _t in run_response.tools or []:
    # Case 1: confirmed tools — execute if confirmed & not yet run
    if _t.requires_confirmation is True and _functions:
        if _t.confirmed is True and _t.result is None:
            deque(run_tool(agent, run_response, run_messages, _t, functions=_functions), maxlen=0)
        else:
            reject_tool_call(agent, run_messages, _t, functions=_functions)
            _t.confirmed = False
            _t.confirmation_note = _t.confirmation_note or "Tool call was rejected"
            _t.tool_call_error = True
        _maybe_create_audit_approval(agent, _t, run_response, "approved" if _t.confirmed is True else "rejected")
        _t.requires_confirmation = False
    elif _t.external_execution_required is True:      # Case 2: splice caller-supplied result
        handle_external_execution_update(agent, run_messages=run_messages, tool=_t)
    elif _t.tool_name == "get_user_input" and _t.requires_user_input is True:   # Case 3a
        handle_get_user_input_tool_update(agent, run_messages=run_messages, tool=_t)
        _t.answered = True
    elif _t.tool_name == "ask_user" and _t.requires_user_input is True:         # Case 3b
        handle_ask_user_tool_update(agent, run_messages=run_messages, tool=_t)
        _t.answered = True
    elif _t.requires_user_input is True:              # Case 4: schema fields -> args, then run
        handle_user_input_update(agent, tool=_t)
        deque(run_tool(...), maxlen=0)
        _t.answered = True
```

**Flow:** Case 1 executes-or-rejects then ALWAYS clears requires_confirmation and writes an audit approval row when approval_type="audit"; unconfirmed tools get a default rejection note rather than silence. Case 2 raises ValueError if the external result is still missing (:601). Cases 3a/3b synthesize tool-role messages ("User inputs retrieved: …" / "User feedback received: …") so the model sees answers as normal tool results; skipping empty schemas avoids repeating tool_call_ids (:615-617). Case 4 copies user_input_schema values into tool_args before running.
**Invariant:** The four cases are mutually exclusive in this order — confirmation wins over user_input, and the two agentic tools are keyed by TOOL NAME (`get_user_input`, `ask_user`) before the generic schema case. The same ladder exists in three more variants (stream/async/async-stream) that must be kept behaviorally identical.
**Probe:** `grep -c '_t.requires_confirmation = False' libs/agno/agno/agent/_tools.py` → **4** (once per variant); direct behavior test `libs/agno/tests/unit/team/test_continue_run_requirements.py::test_top_level_confirmation_true_reaches_tool_execution`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "handle_tool_call_updates requires_confirmation reject_tool_call", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order + flag-clear discipline as the resume contract for any HITL pause taxonomy; adapt tool names/synthesized message wording; omit audit approvals if you don't need an approval ledger.
