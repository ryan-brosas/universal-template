<!-- capsule-v2 -->
# LocationResolverAgent — how does a ReAct agent receive a non-serializable helper through config, and why stream-drain before answering?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How is a stateful GoogleSearchAgent handed to a @tool without globals, and what does the node return when the sub-graph's last message isn't textual?

## Configurable-carried dependency + intent-fallback return
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/task_decomposition_planning/location_resolver_agent/location_resolver_agent.py:search_google` (:29-34), `LocationResolverAgent.__init__` (:46-73), `run` (:80-98).
**Signature:** `run(intent) -> AIMessage` streaming `self.graph.astream(inputs, stream_mode="values", config={"configurable": {"google_search_agent": GoogleSearchAgent.create()}})`.
**Data Shape:** input = raw intent string; output = AIMessage whose content is EITHER the resolved intent (last AIMessage) or the ORIGINAL intent unchanged.

### Decisive source
```python
@tool
async def search_google(implicit_location: str, config: RunnableConfig):
    """Use this to search location in google, can only return location of implicit location"""
    agent = config.get("configurable", {}).get("google_search_agent")
    res = await agent.run(implicit_location)
    return res
```
```python
        async for s in stream:
            message = s["messages"][-1]
            ...
        res_output = intent                      # fallback preset
        if isinstance(message, AIMessage):
            res_output = str(conclude_output)
        return AIMessage(content=res_output)
```

**Flow:** create_react_agent(llm, [search_google], system-prompt-only ChatPromptTemplate) — the search implementation is injected PER INVOCATION through `config["configurable"]["google_search_agent"]`, keeping the @tool module-level and unpicklable-free. The run loop FULLY DRAINS the values stream (logging each step) because astream must be consumed to drive the graph; afterwards the last message becomes the resolved intent ONLY if it's an AIMessage — otherwise the original intent passes through untouched.
**Invariant:** Tool receives dependencies via RunnableConfig, not closure/global — same pattern as the policy subsystem's configurable carrier. Non-AIMessage terminal (tool message last, empty graph result) degrades to identity resolution rather than raising. The docstring constrains the tool to return LOCATION NAMES only ("Do not use your own knowledge to answer").
**Probe:** In-file integration test harness `run_internal_mapping_tests()` (:110-177) maps 22 implicit→explicit cases incl. three N/A impossibles — live-network gated, treat as documented intended behavior, not CI evidence. Deterministic: `grep -n "google_search_agent" src/cuga/backend/cuga_graph/nodes/task_decomposition_planning/location_resolver_agent/location_resolver_agent.py` hits both tool and config sites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "LocationResolverAgent search_google create_react_agent google_search_agent", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt config-carried collaborator agents into @tool functions and drain-before-decide streaming semantics with identity fallback. Adapt the react prompt/toolset. Omit the in-file test main() from ports; use it as behavior documentation.
