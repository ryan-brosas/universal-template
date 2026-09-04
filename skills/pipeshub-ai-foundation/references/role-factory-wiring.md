<!-- capsule-v2 -->
# Role → AgentSpec factory — how does one turn a Role's pure data into a wired AgentSpec with sub-agent composition?

**Source:** pipeshub-ai (Apache-2.0) `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** A porter defining agents as data (roles) must know how `AgentFactory` turns a `Role` (system prompt, allowed tools, model, loop, middleware, named sub-agents) into a complete `AgentSpec`, and how `wire_sub_agents` registers named children as `AgentTool`s on the shared runtime registry so a `Role` can declare full agent-to-agent composition purely as data.

## Role data → AgentSpec
**Path/Symbol:** `runtime/factory.py:AgentFactory` (15-93); `from_role` (37-44); `from_role_obj` (46-76); `wire_sub_agents` (78-93).
**Signature:** `AgentFactory(runtime, role_registry, *, default_provider="anthropic", default_model="claude-sonnet-4-6")`; `from_role(role_name, **overrides) -> AgentSpec`; `from_role_obj(role: Role, **overrides) -> AgentSpec`; `wire_sub_agents(spec, sub_agents: dict[str, AgentSpec]) -> AgentSpec`.
**Data Shape:** `Role` is pure data (no I/O). `AgentSpec` is Layer-0 definitional data. `AgentFactory` is Layer-4, used by `ControlPlane.make_spec()` and dynamic role-based tools (spawn_agent, best_of_n, handoff). `overrides` can replace `model` (str or `ModelSpec`) and `tool_names`; otherwise `tool_names = list(role.allowed_tools)`.

### Decisive source
```python
def from_role_obj(self, role, **overrides):
    model = ModelSpec(provider=self._default_provider, model=role.model or self._default_model)
    model_override = overrides.pop("model", None)
    if isinstance(model_override, str):
        model = model.model_copy(update={"model": model_override})
    elif isinstance(model_override, ModelSpec):
        model = model_override
    tool_names = overrides.pop("tool_names", None)
    if tool_names is None:
        tool_names = list(role.allowed_tools)
    spec_kwargs = {
        "name": role.name, "description": role.description,
        "system_prompt": role.system_prompt, "tool_names": tool_names,
        "capabilities": list(role.capabilities), "model": model,
        "middleware": list(role.middleware),
    }
    if role.loop is not None: spec_kwargs["loop"] = role.loop
    if role.mode is not None: spec_kwargs["mode"] = role.mode
    spec_kwargs.update(overrides)
    spec = AgentSpec(**spec_kwargs)
    if role.sub_agents:
        spec = self.wire_sub_agents(spec, role.sub_agents)
    return spec

def wire_sub_agents(self, spec, sub_agents):
    registry = self._runtime.tool_registry
    tool_names = list(spec.tool_names)
    for tool_name, child_spec in sub_agents.items():
        if not registry.has(tool_name):
            registry.register_tool(AgentTool(child_spec, self._runtime, name=tool_name))
        if tool_name not in tool_names:
            tool_names.append(tool_name)
    return spec.model_copy(update={"tool_names": tool_names})
```

**Flow:** `from_role` resolves a role NAME via `role_registry.resolve` (wrapping unknown-role failure in a `ValueError` listing available names), then delegates to `from_role_obj`. `from_role_obj` builds a `ModelSpec` from runtime defaults + role model, applies `model`/`tool_names` overrides, assembles the `AgentSpec` kwargs (name/description/system_prompt/tool_names/capabilities/model/middleware + optional loop/mode), then if the role declares `sub_agents`, calls `wire_sub_agents` to register each named child as an `AgentTool` on the shared runtime registry (idempotent — re-registering the same name is a no-op) and add its name to the parent's tool list.
**Invariant:** `Role` alone can define a complete agent including named sub-agents — composition is pure data. `wire_sub_agents` is idempotent (no duplicate `AgentTool` registration) and additive (never removes existing tool names). The factory is the single path `ControlPlane` and dynamic role-based tools share, so agent definitions stay consistent. `spec_factory` on `AgentRuntime` is a narrow callable wired to `AgentFactory.from_role` to keep the dependency direction one-way (DIP).

**Probe:** `tests/unit/agents/adapter/test_factory_wiring.py` (pins `deep_mode_wires_spec_factory_for_spawn_agent`, `deep_mode_composes_domain_agents_into_spawn_pool`, `react_mode_composes_domain_agents_by_default`, `composition_kill_switch_off_run_code_does_not_advertise_parent_results`). `tests/unit/agents/adapter/test_domain_agents.py` (pins role→spec wiring incl. `Maximum spawn depth (3) reached`). Graph: `AgentFactory` class + `from_role`/`from_role_obj`/`wire_sub_agents` all indexed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "AgentFactory", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "wire_sub_agents", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Role-as-pure-data → AgentSpec factory shape, the override semantics (`model` str/`ModelSpec`, `tool_names` default to `role.allowed_tools`), and the idempotent `wire_sub_agents` that registers named children as `AgentTool`s on the shared runtime registry. Adopt the DIP `spec_factory` callable to avoid a concrete-factory dependency in `AgentRuntime`. Adapt default provider/model and role-registry resolution to host. Omit the concrete `AgentTool`/`Role` internals — the contract is the data→spec→composition ladder. Direct tests confirm all invariants; index coverage `no_recorded_issue`+`metadata_match` (best-effort caveat).
