<!-- capsule-v2 -->
# InterruptToolNode replay shim — re-materialize a stashed tool_call when a graph re-enters after an interrupt

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When a LangGraph run resumes after `interrupt_after` (or any HITL pause) and lands back on the interrupt node with no new tool calls in the message, how does the pending tool call get executed exactly once?

## The shim converts state.tool_call back into an AIMessage tool_call
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/shared/interrupt_tool_node.py` (`InterruptToolNode.node_handler` :22-30); the node is registered in `interrupt_after=[action_agent.name, interrupt_tool_node.name]` at graph build (see `graph-orchestration.md`).
**Signature:** `async node_handler(state: AgentState, name: str, config: RunnableConfig) -> AgentState` — mutates and returns state.
**Data Shape:** reads `state.tool_call` (the stashed pending call) + last message's tool_calls; appends one empty-content AIMessage named after the node carrying that single tool_call; clears `state.tool_call = None`; sets `state.sender = name`.

### Decisive source
```python
# interrupt_tool_node.py:23-29 — replay ONLY when the resume carried no fresh calls
logger.warning("Returned to interrupt node")
if state.tool_call and len(state.messages[-1].tool_calls) == 0:
    msg = AIMessage(content="", name=name)
    msg.tool_calls = [state.tool_call]
    state.sender = name
    state.messages.append(msg)
    state.tool_call = None
```

**Flow:** first arrival: nothing stashed → transparent pass-through (the warning log is the trace). Resume-after-interrupt arrival: downstream executor already ran and appended its ToolMessage, so the last message has NO tool_calls while `state.tool_call` still holds the pre-interrupt call → the shim re-emits it as a synthetic AIMessage so normal tool-execution routing picks it up; the stash is cleared in the SAME update so the call can never double-execute.
**Invariant:** the two-condition gate is the whole contract — replay only on (stash present AND last message has zero tool_calls); clearing the stash unconditionally after use prevents replays looping forever; sender must be set to THIS node or downstream routing replies to the wrong address.
**Probe:** no dedicated unit suite at HEAD — pinned e2e via policy full-graph tests (`cuga_graph/policy/tests/test_e2e_*.py`) and supervisor HITL suites exercising interrupt/resume paths (coverage caveat).
**Retrieve:**
```python
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "InterruptToolNode node_handler replay tool_call", limit: 5 });
```

## Verdict
Adopt the guarded-replay pattern for any interrupt_after-based HITL design: stash the pending call in state before pausing, and let the interrupt landing node re-materialize it exactly once. Adapt message construction to your state schema. Omit the specific logger.warning if you have structured tracing.
