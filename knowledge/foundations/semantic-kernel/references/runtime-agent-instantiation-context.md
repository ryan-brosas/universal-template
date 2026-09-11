<!-- capsule-v2 -->
# Runtime agent instantiation context — why agents cannot be constructed directly, and what register() wires

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Why does constructing an agent outside a runtime raise, and what exactly does `BaseAgent.register` wire beyond the factory?

## AgentInstantiationContext + register/register_factory/_get_agent
**Path/Symbol:** `python/semantic_kernel/agents/runtime/in_process/agent_instantiation_context.py:AgentInstantiationContext` (whole, 65 ln), `core/base_agent.py:BaseAgent.__init__` (95–113), `register` (181–221), `in_process/in_process_runtime.py:register_factory` (729–757), `_invoke_agent_factory` (759–793), `_get_agent` (795–806).
**Signature:** `async def register(cls, runtime, type: str, factory, *, skip_class_subscriptions=False, skip_direct_message_subscription=False) -> AgentType`; `async def register_factory(self, type, agent_factory, *, expected_class=None) -> AgentType`; `async def _get_agent(self, agent_id: AgentId) -> Agent`.
**Data Shape:** `AgentInstantiationContext` wraps a `ContextVar[tuple[CoreRuntime, AgentId]]` set only inside `_invoke_agent_factory`; `BaseAgent` stores `_runtime` + `_id` from it; the runtime memoizes instances in `_instantiated_agents: dict[AgentId, Agent]`.

### Decisive source
```python
# BaseAgent.__init__ — direct construction is impossible by design
try:
    runtime = AgentInstantiationContext.current_runtime()
    id = AgentInstantiationContext.current_agent_id()
except LookupError as e:
    raise RuntimeError(
        "BaseAgent must be instantiated within the context of an AgentRuntime. It cannot be directly "
        "instantiated."
    ) from e

# register_factory — duplicate type strings rejected, expected_class validated at instantiation
if type.type in self._agent_factories:
    raise ValueError(f"Agent with type {type} already exists.")
async def factory_wrapper() -> T:
    maybe_agent_instance = agent_factory()
    ...
    if expected_class is not None and type_func_alias(agent_instance) != expected_class:
        raise ValueError("Factory registered using the wrong type.")
    return agent_instance

# _get_agent — lazy per-AgentId instantiation
if agent_id in self._instantiated_agents:
    return self._instantiated_agents[agent_id]
...
agent = await self._invoke_agent_factory(agent_factory, agent_id)
self._instantiated_agents[agent_id] = agent
```

**Flow:** `_invoke_agent_factory` populates the contextvar `(runtime, agent_id)` around the factory call, so `BaseAgent.__init__` (and any user code in the factory via `AgentInstantiationContext.current_agent_id()`) can read its identity; a LookupError there becomes the "cannot be directly instantiated" RuntimeError. Factories take 0 args (or 2 — deprecated with a warning); sync or async results both accepted; `expected_class` is checked at INSTANTIATION time, not registration. `_get_agent` lazily instantiates on first message, memoized per AgentId. `BaseAgent.register` (the ergonomic entry) does four things: registers the factory with `expected_class=cls`; binds class-level `@default_subscription`/`@type_subscription` decorated subscriptions under `SubscriptionInstantiationContext.populate_context(agent_type)` (so DefaultSubscription can detect its agent type); adds the direct-message prefix subscription; registers known serializers from `_handles_types()`. Both skip flags allow opting out. Construction failures inside the runtime are logged (`AgentConstructionExceptionEvent`) and propagate to the publish arm's error path, not the caller.
**Invariant:** An agent instance always has exactly one (runtime, AgentId) identity fixed at construction and never changes; one instance per AgentId per runtime (memoized). Duplicate agent type strings fail at registration, wrong classes fail at first instantiation.
**Probe:** `python/tests/unit/agents/runtime/test_runtime.py::test_agent_type_register_factory` (line 129 — wrong expected_class raises ValueError; factory reads `AgentInstantiationContext.current_agent_id()`), `test_agent_type_must_be_unique` (154 — duplicate type raises), `test_register_receives_publish_with_construction` (205 — factory raising ValueError logs "Error constructing agent", runtime still stops idle).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "AgentInstantiationContext BaseAgent register register_factory _get_agent _invoke_agent_factory SubscriptionInstantiationContext", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the contextvar identity-injection pattern (agents can never exist without a runtime-assigned identity), lazy per-id instantiation with memoization, and register() as the four-wire entry (factory + class subscriptions + prefix subscription + serializers). Adapt the deprecation path for 2-arg factories (just drop it). Omit the `try_get_underlying_agent_instance` escape hatch if your host forbids reaching into actor internals.
