<!-- capsule-v2 -->
# Supervisor prepare node — per-run tool-context assembly with fresh-conversation todo reset and policy gate

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A supervisor graph must assemble its ENTIRE tool surface (delegation tools, todos, runtime fs/shell, skills, provider tools) into one executable namespace + one prompt EVERY turn — how do you keep that namespace from leaking across concurrent runs, and which state must reset on a fresh conversation vs persist across turns?

## The prepare contract
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_supervisor/nodes/prepare_agents_and_prompt.py` (`create_prepare_agents_and_prompt_node` :35-289; `_store_todos_on_run_state` :41-50; policy gate :66-85; agent loop :99-175; budget reset :275-282).
**Signature:** `prepare_agents_and_prompt(state: CugaSupervisorState, config) -> Command(goto="call_model", update={tools_prepared, prepared_prompt, step_count=0, available_agents, [metadata], [task_todos], tool_calls_used_run=0, tool_budget_exhausted})`.
**Data Shape:** tools registered into `adapter._agent_tools_context` (name→callable) AND described in `agent_tools_for_prompt` dicts (`name/description/params_str/params_doc/response_doc`) rendered into the jinja2 template as `tools`.

### Decisive source
```python
# :57-59 — fresh-conversation detection drives the ONLY state reset here
is_fresh_conversation = len(state.supervisor_chat_messages or []) <= 1
if is_fresh_conversation:
    state.task_todos = None

# :41-47 — todos write onto the RUN's state via exec context, never a shared list
# The create_update_todos tool runs inside ``execute_agent_tool``; the per-run
# execution context resolved here points at that run's CugaSupervisorState, so
# concurrent conversations never share a todo list.

# :133-137 — delegation tools built per-agent at PREPARE time, stored on adapter
tool_name = f"delegate_to_{agent_name}"
tool_func = create_agent_delegation_func(adapter, agent_name, agent_or_config, agent_card=agent_card)
adapter._agent_tools_context[tool_name] = tool_func

# :275-282 — run budget resets each invocation; thread ceiling deliberately NOT
# Per-task tool-call budget resets here: prepare runs once per graph
# invocation (START -> prepare), so each user turn starts fresh. See the
# matching reset in the CugaLite prepare node — including why
# tool_calls_used_thread must NOT be reset alongside it.
update_payload["tool_calls_used_run"] = 0
update_payload["tool_budget_exhausted"] = thread_budget_exhausted(
    getattr(state, "tool_calls_used_thread", 0))
```

**Flow:** fresh-conversation check → optional policy enactment (INTENT_GUARD/PLAYBOOK/TOOL_GUIDE via `PolicyEnactment.check_and_enact`; a returned command short-circuits with `task_todos=None` folded in when fresh) → per-agent loop classifies internal CugaAgent vs external dict (fetching A2A cards for http+sdk peers, degrading description on fetch failure) → builds one `delegate_to_{name}` closure per agent → registers todos tool (writer targets run-local state), runtime bundle (`resolve_runtime_backends` honoring config overrides), skill tools when enabled, then provider tools (provider failure = logged warning, never fatal) → composes special instructions + skills block + execution split-note → renders prompt template → emits update Command. Prompt-visible signatures differ by variable support: A2A+pass_variables advertises `variables` ("passed in request metadata"), plain A2A hides it.
**Invariant:** the adapter's `_agent_tools_context` is a NAME REGISTRY rebuilt each turn — runtime values travel via the per-execution context (see supervisor-delegation.md), never inside these closures. Only `task_todos` and the run counter reset on freshness/new-turn; the thread budget ceiling and supervisor history always persist. Provider/skill/card failures degrade to fewer prompt tools with warnings — assembly NEVER fails the turn.

**Probe:** direct tests `tests/test_supervisor_graph_adapter.py` (::test_messages_key_is_supervisor_chat_messages :39-41, factory-returns-async :127-138, todos-in-system-content :141-151); `test_delegation_recording.py::test_prepare_system_content_injects_run_local_task_todos` (:30-35); `tests/test_execution_context.py::test_resolve_supervisor_execution_context_from_locals`. Node body itself untested — COVERAGE CAVEAT.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "create_prepare_agents_and_prompt_node _agent_tools_context PolicyEnactment resolve_runtime_backends delegate_to", limit: 10 });
```

## Verdict
Adopt prepare-time registry rebuild + run-scoped todo writer + fresh-vs-persistent state split for any conversational graph that regenerates its tool surface per turn; adopt degrade-not-fail assembly so one broken provider never kills the conversation. Adapt the tool-info dict shape to your prompt renderer. Omit nothing.
