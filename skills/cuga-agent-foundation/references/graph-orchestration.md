<!-- capsule-v2 -->
# Graph Orchestration — a policy-governed agent graph with subgraph nodes and conditional-edge-safe stubs

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you assemble a multi-mode agent (chat, task decomposition, browser/API execution, Lite tool loop, supervisor delegation) into one StateGraph without runtime routing errors when optional subsystems are disabled?

## DynamicAgentGraph: build-time validation, runtime config
**Path/Symbol:** `src/cuga/backend/cuga_graph/graph.py` (`DynamicAgentGraph.__init__` :64-114, `build_graph` :116-128, `add_nodes` :149-415, `_cuga_supervisor_stub` :410-415, `add_edges` :417-433).

**Signature:** `await build_graph()` → `graph.compile(checkpointer=MemorySaver(), interrupt_after=[action_agent.name, interrupt_tool_node.name])`.

**Data Shape:** ~18 nodes incl. two compiled SUBGRAPHS added as nodes (`"CugaLiteSubgraph"` → `"CugaLiteCallback"`, optionally `"CugaSupervisorSubgraph"` → `"CugaSupervisorCallback"`); edges fixed at START→Chat, TaskDecomposition→PlanController, InterruptToolNode→PlanController, QA→BrowserPlanner, ActionAgent→BrowserPlanner, FinalAnswer→END; all dynamic branching done inside nodes via returned `Command(goto=...)`, not conditional edges.

### Decisive source
```python
# graph.py:284-287 + 408-415 — optional subsystem still gets a node so that
# TaskAnalyzer's conditional edges validate at compile time:
if getattr(settings.supervisor, 'enabled', False):
    graph.add_node(self.cuga_supervisor.name, self.cuga_supervisor.node)
    ...
else:
    async def _cuga_supervisor_stub(state, config=None):
        from langgraph.types import Command
        return Command(update=state.model_dump(), goto="CugaLite")
    graph.add_node(self.cuga_supervisor.name, _cuga_supervisor_stub)
```
And the policy handoff comment (:263-266): the CugaLite subgraph is built WITHOUT the policy system because "LangGraph automatically passes the config down to the subgraph's nodes ... where PolicyEnactment.check_and_enact() extracts it."

**Flow:** constructor instantiates every agent once → `build_graph` adds nodes/edges → ToolGuard wraps the tool provider BEFORE the Lite subgraph is built (so apps_list for prompts comes from the wrapped provider) → LLM resolved from published llm_config with graceful fallback to TOML settings on creation failure (:200-214) → compile with checkpointer + interrupt_after for HITL pause points → per-invocation config carries policy_system/special_instructions.

**Invariant:** LangGraph validates that every edge target names an existing node — so a disabled supervisor can't just be omitted while TaskAnalyzer holds a conditional edge to it. The stub-node pattern (present at build time, never taken at runtime) is what keeps one static topology serving all feature-flag combinations.

**Probe:** Full-graph e2e suites under `src/cuga/backend/cuga_graph/policy/tests/` (e.g. `test_tool_approval_full_graph.py`) run this exact assembly with policies enabled — they are the direct tests of the wiring. Caveat: no unit test isolates the stub branch; verify by compiling with `supervisor.enabled=false` if you port the pattern.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "DynamicAgentGraph build_graph interrupt_after supervisor stub", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-static-topology + Command-based dynamic routing, compiled-subgraph-as-node, stub nodes for flag-disabled branches, and interrupt_after HITL points. Adapt node roster to your product surface. Omit the demo default agents and YAML supervisor-config loading unless you need the same delegation product.
