<!-- capsule-v2 -->
# Shared agent graph builder — ONE uncompiled 3-node topology serving Lite and Supervisor

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do two different agents (CugaLite sandbox loop, CugaSupervisor delegation loop) share one LangGraph structure without drifting, while each keeps its own node names and checkpointer?

## build_agent_graph wires START → prepare → call_model ↔ execute
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_agent_core/graph/shared_graph.py` (`build_agent_graph(*, adapter, state_class, prepare_node, call_model_node, execute_node) -> StateGraph` :25-61); consumed via `CoreGraphAdapter.execute_node_name` (see `core-graph-adapter.md`).
**Signature:** keyword-only factory returning an UNCOMPILED `langgraph.graph.StateGraph`; third node is named dynamically as `graph.add_node(adapter.execute_node_name, execute_node)` so Lite gets `"sandbox"` and Supervisor gets `"execute_agent_tool"`.
**Data Shape:** inputs are the graph-specific Pydantic state class (`CugaLiteState` / `CugaSupervisorState`) plus three async node functions produced by adapter factories; output is a raw `StateGraph` the caller must `.compile(checkpointer=...)`.

### Decisive source
```python
# shared_graph.py:53-60 — the two edges are asymmetric ON PURPOSE
graph.add_edge(START, "prepare")
# prepare returns Command(goto=...) — no static edge (avoids call_model after BLOCK_INTENT).
# Execute node returns a state update (not Command); loop back for the NL answer.
graph.add_edge(adapter.execute_node_name, "call_model")
```
The docstring pins the rest of the topology: `START → prepare --Command--> call_model ↔ execute (loop) → END`.

**Flow:** prepare emits a `Command(goto=...)` (so policy BLOCK_INTENT can jump straight to END — a static prepare→call_model edge would fire call_model after a block); call_model ↔ execute form the loop; execute returns plain state updates, never Commands. Compilation is deliberately left to each call site so thread-scoped memory (e.g. the SDK's runtime checkpointer) can differ per entry point.
**Invariant:** NEVER add a static edge out of `prepare`; NEVER compile inside the builder; node identity of the executor comes ONLY from the adapter so both graphs keep their historical node names (checkpoint compatibility).
**Probe:** `src/cuga/backend/cuga_graph/nodes/cuga_agent_core/tests/graph/test_shared_graph_builder.py` (:67-79 compiles with the Lite adapter naming `sandbox`; suite also asserts supervisor `execute_agent_tool` naming, START→prepare→call_model edges, and compile success against mock nodes).
**Retrieve:**
```python
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "build_agent_graph", limit: 5 });
```

## Verdict
Adopt the uncompiled-return + adapter-named-execute-node + Command-from-prepare trio as a unit — they jointly prevent the two classic wrong ports (double call_model after intent blocks; shared compiled graph freezing one checkpointer for all callers). Adapt state class and hook functions per host. Omit the specific node-name strings outside CUGA.
