<!-- capsule-v2 -->
# ACP approval scope ladder — how does a remembered "always allow" stay safe when tool arguments are arbitrary model output?

## Source / Question
`pydantic_ai_harness` (MIT) `main@76db3dec`; Codebase Memory project `pydantic-ai-harness`. **Question:** When a client approves a tool call "always", what exact key stores that decision so it neither re-prompts for the same logical call nor silently approves *different* calls — and what happens to calls the agent wants the CLIENT to execute instead of merely approve?

## Path / Symbol
`pydantic_ai_harness/experimental/acp/_adapter.py` — `PydanticAIACPAgent._resolve_approvals` (:783–825); `pydantic_ai_harness/experimental/acp/_permission.py` — `default_permission_scope` (:30–37); session memory `SessionState.always_allow/always_reject: set[Hashable]` (`_session.py` :93–108).

**Signature:**
```python
async def _resolve_approvals(self, turn: _TurnState, state: SessionState[AgentDepsT],
                             requests: DeferredToolRequests) -> DeferredToolResults
def default_permission_scope(call: ToolCallPermission) -> Hashable
```

**Data Shape:** Input `DeferredToolRequests` splits model-demanded tool interactions into `.approvals` (harness-executed tools flagged `requires_approval=True`) and `.calls` (client-executed). Output `DeferredToolResults.approvals: dict[tool_call_id, bool | ToolDenied]`. Scope key default = `(tool_name, json.dumps(jsonable(args), sort_keys=True))`; hosts may inject any `Hashable` via `permission_policy`.

### Decisive source
```python
        if requests.calls:
            names = sorted({call.tool_name for call in requests.calls})
            raise acp.RequestError.internal_error(
                {'reason': 'external tool execution is not supported by the ACP adapter', 'tools': names}
            )
# ...
            # `args_as_dict()` canonicalizes the call's arguments to a dict: a model may deliver them
            # as a JSON string (the OpenAI default ...), and a raw string would make the scope key
            # sensitive to key order, defeating a remembered "always" decision for what is the same
            # logical call.
            scope = self._permission_policy(
                ToolCallPermission(tool_name=call.tool_name, tool_call_id=call.tool_call_id, args=call.args_as_dict())
            )
            if scope in state.always_allow:
                results.approvals[call.tool_call_id] = True
                await self._mark_running(turn, call.tool_call_id)
                continue
```
And the default scope (_permission.py :30–37):
```python
    return (call.tool_name, json.dumps(jsonable(call.args), sort_keys=True))
```

**Flow:** per approval request → canonicalize args (`args_as_dict()`) → compute scope → remembered-allow short-circuits with `_mark_running`; remembered-reject yields `ToolDenied('Rejected by the client.')` and records `turn.denied.add(id)` (so the later result event reports failed) without ever promoting the call to running; otherwise ask the client (`_request_permission`) → deny keeps status pending-until-failed, approve promotes to in_progress. Rejected calls' ids land in `turn.denied` either way.

**Invariant:** "Always" decisions are scoped EXACTLY by default — same tool + same canonical arguments — never widened implicitly; scopes are per-session state (`always_allow`/`always_reject` live on `SessionState`, not the adapter), so one session's grant cannot leak into another. Only an APPROVED call is ever shown as running. Client-side tool execution requests are refused loudly as an internal error naming the offending tools.

**Probe:** `bash -c 'cd $REFERENCE_ROOT/pydantic-ai-harness && /tmp/harness-p6-venv/bin/python -m pytest "tests/experimental/acp/test_acp.py::TestPermission::test_permission_policy_can_widen_scope_to_the_tool_name" "tests/experimental/acp/test_acp.py::TestPermission::test_always_decisions_are_isolated_per_session" "tests/experimental/acp/test_acp.py::TestPermission::test_external_tool_calls_are_rejected" "tests/experimental/acp/test_acp.py::TestPermission::test_mixed_approvals_in_one_turn" -q'` — widened policy covers different args after ONE prompt; isolation demands 2 prompts across sessions; external calls raise; mixed turn runs only the approved tool. (Executed this pass; see verification.md.)

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "default_permission_scope always_allow ToolCallPermission args_as_dict", limit: 5 });
```
Observed live: rank#1 `default_permission_scope` (_permission.py :30–37) beside `ToolCallPermission`; `_resolve_approvals` (:783–825) resolves with callers `prompt`→`_run_turn`.

## Verdict
**Adopt** canonical-JSON scope keying (`sort_keys` + args-as-dict normalization) for any approval-memory keyed on model-produced arguments, and keep the memory per-session unless explicitly shared. **Adopt** the deny-path discipline: rejected calls must not render as running and their eventual results must be marked denied/failed. **Adopt** refusing unsupported execution modes with a structured error listing the tools. **Adapt** the scope function — widening to tool name alone is a supported, tested configuration (`permission_policy=lambda call: call.tool_name`), not a behavior change. **Omit** ACP request/response plumbing. Caveat: none — four direct tests pin the ladder at this pin.
