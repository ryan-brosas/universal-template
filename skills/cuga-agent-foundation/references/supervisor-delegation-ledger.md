<!-- capsule-v2 -->
# Supervisor delegation ledger — record_delegation state fan-out with policy-decision re-parenting

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When a supervisor's generated script calls sub-agents, what exactly must be persisted back onto supervisor state per delegation — and how do a sub-agent's POLICY decisions stay attributable to the right agent in the parent's audit metadata?

## The ledger contract
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_supervisor/supervisor_graph_adapter.py` (`SupervisorGraphAdapter.record_delegation` :98-139); consumed by `_record_delegation` (`delegation.py:66-86`) which resolves the ambient execution context and no-ops silently when absent.
**Signature:** `record_delegation(state, agent_name, *, result, answer, variables: Optional[Dict[str, Any]]) -> None` (mutates state in place; returns None).
**Data Shape:** five state lanes updated — `selected_agents: List[str]`, `agent_results: Dict[str, Any]`, `agent_variables: Dict[str, Dict]`, `agent_chat_messages: Dict[str, List[BaseMessage]]`, `metrics: Dict`; plus `supervisor_metadata.policy_decisions` via `PolicyDecision.model_copy(update={"agent_name": agent_name})`.

### Decisive source
```python
# supervisor_graph_adapter.py:111-121 — membership + result/variables/messages fan-out
if agent_name not in state.selected_agents:
    state.selected_agents.append(agent_name)
state.agent_results[agent_name] = answer
if variables:
    state.agent_variables[agent_name] = dict(variables)
chat_messages = getattr(result, "chat_messages", None) if result is not None else None
if chat_messages:
    state.agent_chat_messages[agent_name] = list(chat_messages)

# :123-133 — THE invariant: sub-agent policy decisions are RE-PARENTED with the
# delegating agent stamped on each decision before joining the supervisor audit log
delegated_decisions = getattr(result, "policy_decisions", None) if result is not None else None
if delegated_decisions:
    metadata = dict(self.get_metadata(state))
    append_policy_decisions(metadata, [
        PolicyDecision.model_validate(decision).model_copy(update={"agent_name": agent_name})
        for decision in delegated_decisions
    ])
    self.set_metadata(state, metadata)

# :135-139 — metrics: monotonic count + last-delegated pointer
metrics["delegation_count"] = int(metrics.get("delegation_count", 0)) + 1
metrics["last_delegated_agent"] = agent_name
```

**Flow:** every delegation branch (internal CugaAgent invoke, A2A SDK, legacy A2A, unknown-type error string) funnels through `_record_delegation`, which resolves the per-run `SupervisorExecutionContext` from the call stack; with no active context it silently no-ops (delegation funcs must work standalone). The execute node then snapshots ALL five lanes into its LangGraph update via `_delegation_state_update(state)` (:29-37) — plain-dict copies, so checkpointed state gets fresh objects instead of aliases.
**Invariant:** attribution is explicit — a child's policy decisions would otherwise blend anonymously into the parent's audit trail, so each is validated and copied with `agent_name` overwritten BEFORE append. Unknown agent types still produce an ANSWER STRING through the same recording path (error-as-answer, never raise out of generated code). Every lane the node later reads must be in the update snapshot or LangGraph keeps stale checkpoint values.

**Probe:** direct tests `tests/test_delegation_recording.py`: `::test_record_delegation_updates_state_fields` (:90-129, pins all five lanes incl. `decision["agent_name"] == "crm_agent"`), `::test_create_update_todos_writes_to_run_local_state_via_exec_context` (:45-73), variable-forwarding matrix `::test_a2a_sdk_variable_forwarding` / `::test_legacy_a2a_variable_forwarding` (:311-334, omitted/explicit/empty × sdk/legacy), `::test_legacy_a2a_does_not_send_variables_when_setting_off` (:339-342).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "record_delegation selected_agents agent_results policy_decisions _delegation_state_update", limit: 10 });
```

## Verdict
Adopt the five-lane delegation ledger + explicit re-parenting of child governance decisions with agent stamps for ANY supervisor-of-agents design; adopt error-as-answer recording so generated scripts never see exceptions from bad targets. Adapt lane names/metadata schema to your host. Omit nothing.
