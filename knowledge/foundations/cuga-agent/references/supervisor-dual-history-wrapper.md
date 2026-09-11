<!-- capsule-v2 -->
# Supervisor dual-history wrapper — AgentState↔subgraph state conversion with checkpointer-proof message restoration

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A LangGraph parent graph routes a turn INTO a state-superset subgraph (and back), while a checkpointer persists messages as plain dicts between turns. How do you convert states in both directions without merging the parent's and subgraph's conversation histories — or crashing on restored dict-messages?

## The wrapper contract
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_supervisor/cuga_supervisor_node.py` (`CugaSupervisorNode.node` :33-201, lazy `_subgraph` :27/:39-43); `cuga_supervisor/cuga_supervisor_state.py` (`CugaSupervisorState(AgentState)` :22-70).
**Signature:** `async node(state: AgentState, config) -> Command` (returns `Command(update=result_dict, goto="CugaSupervisorCallback")` on success, `goto="FinalAnswerAgent"` on any failure); `ensure_message_objects(messages) -> list[BaseMessage]` (inner helper :58-82).
**Data Shape:** `CugaSupervisorState` extends `AgentState` adding `supervisor_chat_messages: List[BaseMessage]`, `available_agents/selected_agents/agent_results/agent_variables/agent_chat_messages/supervisor_variables`, `tools_prepared/prepared_prompt/script/execution_complete/step_count`, `supervisor_metadata`. The wrapper round-trips `state.model_dump()` → subgraph → `result_dict`.

### Decisive source
```python
# cuga_supervisor_node.py:53-54 — the ONE rule that keeps histories separate
# Initialize supervisor_chat_messages - only use supervisor_chat_messages, never chat_messages
# chat_messages is for internal sub-agents, supervisor has its own conversation history

# :86-91 — checkpointer round-trip turns message objects into dicts; restore BEFORE subgraph
if state.supervisor_chat_messages and len(state.supervisor_chat_messages) > 0:
    supervisor_state_dict["supervisor_chat_messages"] = ensure_message_objects(
        state.supervisor_chat_messages)

# :116-118 — input dedup: only append if the LAST message isn't already this input
if not last_msg or not isinstance(last_msg, HumanMessage) or last_msg.content != state.input:
    supervisor_state_dict["supervisor_chat_messages"].append(HumanMessage(content=state.input))

# :156-157 — copy on the way OUT so the returned update doesn't alias the result object
supervisor_msgs = list(supervisor_msgs) if supervisor_msgs else []

# :178-184 — answer fallback ladder: subgraph final_answer → last supervisor message
if "final_answer" not in result_dict or not result_dict.get("final_answer"):
    last_msg = result_dict["supervisor_chat_messages"][-1]
    if hasattr(last_msg, 'content') and last_msg.content:
        result_dict["final_answer"] = last_msg.content
```

**Flow:** unset subgraph ⇒ log error, set canned `final_answer`, `goto FinalAnswerAgent` (never raise out of a graph node). Otherwise: dump AgentState → restore dict-messages to objects (`type`/`role` sniffing: Human→HumanMessage, AI→AIMessage, content-presence fallback) → initialize empty supervisor history on first turn → append current `state.input` unless already last → build `CugaSupervisorState(**dict)` → `await self._subgraph.ainvoke(...)` → normalize result (State | dict | model_dump duck-typing) → preserve/copy supervisor messages → final-answer fallback → `Command(update, goto="CugaSupervisorCallback")`. Any exception ⇒ same FinalAnswerAgent landing with `f"Error in supervisor execution: {e}"`.
**Invariant:** the two history lanes NEVER mix — `chat_messages` belongs to internal sub-agents, `supervisor_chat_messages` to the supervisor thread, and only the latter crosses the subgraph boundary in either direction. Message objects must be rehydrated after every checkpoint read (pydantic dumps degrade them to dicts; LangChain nodes need objects). User input dedup is positional (last-message compare) because interrupt/resume replays re-deliver the same input. Errors degrade to a final answer string — the wrapper is total (no throw path).

**Probe:** no dedicated unit test pins `CugaSupervisorNode.node` itself — COVERAGE CAVEAT; behavior is constrained indirectly by `tests/test_supervisor_graph_adapter.py` (key names) and the sibling CugaLite node tests (`cuga_lite/tests/test_cuga_lite_node.py`). Deterministic probes: source needles above; graph retrieval below resolves `CugaSupervisorNode.callback_node` :203-359.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "CugaSupervisorNode ensure_message_objects supervisor_chat_messages CugaSupervisorState", limit: 10 });
```

## Verdict
Adopt the dual-lane history split plus dump→rehydrate→invoke→copy-back wrapper shape for ANY parent-graph→subgraph delegation over a checkpointer; adopt the positional input-dedup guard whenever interrupts replay user turns. Adapt state-class names and the fallback ladder depth to your host. Omit the verbose logging (it is debug scaffolding, not contract).
