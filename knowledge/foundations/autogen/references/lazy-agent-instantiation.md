<!-- capsule-v2 -->
# Lazy factory instantiation — when do agents actually get built, and how are duplicate registrations caught?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** What separates registering an agent type from having an instance, and which mistakes raise immediately?

## Factories keyed by type string; instances materialize on first addressable use
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py` (`register_factory` :886–914, `_get_agent` :976–986, `register_agent_instance` :916–940, `_invoke_agent_factory` :942–974).
**Signature:** `async def register_factory(self, type: str | AgentType, agent_factory: Callable[[], T | Awaitable[T]], *, expected_class: type[T] | None = None) -> AgentType`.
**Data Shape:** `_agent_factories: Dict[str, factory_wrapper]`, `_instantiated_agents: Dict[AgentId, Agent]`, `_agent_instance_types: Dict[str, Type[Agent]]`. The wrapper awaits sync-or-async factories and enforces `expected_class`.

### Decisive source
```python
if type.type in self._agent_factories:
    raise ValueError(f"Agent with type {type} already exists.")
...
async def _get_agent(self, agent_id: AgentId) -> Agent:
    if agent_id in self._instantiated_agents:
        return self._instantiated_agents[agent_id]
    if agent_id.type not in self._agent_factories:
        raise LookupError(f"Agent with name {agent_id.type} not found.")
    agent = await self._invoke_agent_factory(agent_factory, agent_id)
    self._instantiated_agents[agent_id] = agent      # ONE instance per AgentId, ever
    return agent
```
```python
# register_agent_instance: mixing factories and raw instances on one type fails loud
if self._agent_factories[agent_id.type].__code__ != agent_factory.__code__:
    raise ValueError("Agent factories and agent instances cannot be registered to the same type.")
```

**Flow:** `register()` stores the (wrapped) factory — nothing constructed yet → first `send_message`/publish/subscriber-resolution touching `AgentId(type, key)` triggers construction under `AgentInstantiationContext.populate_context((runtime, agent_id))` so the agent's `__init__` can discover its runtime/id → cached forever.
**Invariant:** one factory per TYPE (dup raises), one instance per AgentId (cache), constructor errors emit `AgentConstructionExceptionEvent` then re-raise; a placeholder factory raising RuntimeError (:921–924) exists so publishing to an instance-registered type WITHOUT its subscription yields a diagnostic about `skip_class_subscriptions` instead of a silent miss.
**Probe:** `python/packages/autogen-core/tests/test_runtime.py::test_agent_type_register_factory` / `::test_agent_type_must_be_unique` / `::test_agent_type_register_instance_different_types` (instance/type mixing rejected).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "register_factory _get_agent _invoke_agent_factory instantiated_agents", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy per-id instantiation with construction-time context injection — it keeps registration cheap and makes per-key state trivial. Adapt the factory arity check (0 or deprecated 2 args, warns) away entirely in new hosts. Omit the `try_get_underlying_agent_instance` escape hatch outside tests.
