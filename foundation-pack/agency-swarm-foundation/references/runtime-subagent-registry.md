<!-- capsule-v2 -->
# Runtime-scoped subagent registration — how do you add one send_message tool per CLASS and grow recipients without rebuilding schemas?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** Where do the recipient map, pending set, lock, and tool instances live so multiple flows to different targets share ONE tool, and how does late registration update the LLM-visible schema?

## AgentRuntimeState-keyed tool registry with schema mutation
**Path/Symbol:** `src/agency_swarm/agent/subagents.py:register_subagent` (:34-129) + `src/agency_swarm/agent/context_types.py:AgentRuntimeState` (:17-54).
**Signature:** `register_subagent(agent, recipient_agent, send_message_tool_class=None, runtime_state=None) -> None`; `AgentRuntimeState` fields: `tool_concurrency_manager`, `subagents: dict[str, Agent]`, `send_message_tools: dict[str, SendMessage]`, `pending_per_thread: dict[int|None, set[str]]`, `handoffs: list`, `pending_lock: asyncio.Lock`; `scoped_oauth_mcp_tools(user_id)`.
**Data Shape:** tool keyed by CLASS NAME (`send_message_cls.__name__`) — one instance per custom SendMessage subclass per sender, NOT per recipient; recipients dict is SHARED BY REFERENCE with runtime state (`self.recipients = self._runtime_state.subagents` in SendMessage.__init__), so every registration is immediately visible to the existing tool.

### Decisive source
```python
if recipient_key not in runtime_state.subagents:
    runtime_state.subagents[recipient_key] = recipient_agent
send_message_tool = runtime_state.send_message_tools.get(tool_key)
if send_message_tool is None or not isinstance(send_message_tool, send_message_cls):
    try:
        send_message_tool = send_message_cls(sender_agent=agent,
            recipients={recipient_key: recipient_agent}, runtime_state=runtime_state)
    except TypeError:                                   # legacy subclass w/o runtime_state kwarg
        send_message_tool = send_message_cls(sender_agent=agent, recipients={recipient_key: recipient_agent})
    _attach_one_call_guard(send_message_tool, agent)
    runtime_state.send_message_tools[tool_key] = send_message_tool
else:
    if not getattr(send_message_tool, "_one_call_guard_installed", False):
        _attach_one_call_guard(send_message_tool, agent)
    send_message_tool.add_recipient(recipient_agent)     # MUTATES enum + description in place
```
```python
# add_recipient → _update_schema (SendMessage): live schema rewrite
self.params_json_schema["properties"]["recipient_agent"]["enum"] = [a.name for a in self.recipients.values()]
```

**Flow:** lowercase recipient key → dedupe into `subagents` → resolve effective class (instance passed ⇒ its class; None ⇒ base SendMessage) → create-once-per-class with guard, else re-guard + `add_recipient` → tools are attached at RUN time from `runtime_state.send_message_tools` inside `Agent.get_all_tools` (static list filtered of stale MCP tools, then runtime send-message + OAuth tools appended with id-dedup).
**Invariant:** (1) Self-registration raises (`Agent cannot register itself as a subagent.`); (2) the pending-guard state must be shared across all of a sender's tools — that's why `_pending_per_thread`/`_pending_lock` come from runtime state, not the instance (two tool classes for one sender otherwise keep independent backpressure sets); (3) `add_recipient` updates BOTH the enum AND the description roster — updating only the schema leaves the model choosing recipients by a stale role list; (4) standalone fallback (no runtime state) keeps agent-local dicts so direct Agent use still works.
**Probe:** `tests/test_agent_modules/test_agent_subagents.py::test_register_subagent` (:6), `test_register_subagent_adds_send_message_tool` (:14), `test_register_subagent_idempotent` (:22); cross-tool-class behavior pinned by `tests/test_agency_modules/test_agent_flow_integration.py::test_runtime_registration_keeps_multiple_send_message_tool_classes` (:157).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "register_subagent runtime_state send_message_tools", limit: 10 });
```

## Verdict
Adopt class-keyed single-tool registries with reference-shared recipient maps and live schema mutation on late registration; adapt the runtime-state dataclass into your per-agent context object; omit the legacy-TypeError fallback only if you control all subclasses. Probes green at HEAD.
