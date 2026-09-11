<!-- capsule-v2 -->
# Team topic topology — what wires participants, manager, and output stream together inside one team?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** How does a group chat map its members onto the core runtime without name collisions across teams?

## UUID-suffixed topic types; broadcast topic vs direct topics vs output tap
**Path/Symbol:** `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py` (`__init__` :66–151, `_init` :191–245).
**Signature:** `BaseGroupChat.__init__(..., group_chat_manager_name: str, group_chat_manager_class: type[SequentialRoutedAgent], termination_condition, max_turns, runtime: AgentRuntime | None = None, ...)`.
**Data Shape:** Per-instance constants: `_team_id = str(uuid4())`; `_group_topic_type = f"group_topic_{team_id}"`; manager topic `f"{manager_name}_{team_id}"`; participant topics `f"{name}_{team_id}"` (agent TYPE == topic TYPE per participant); `_output_topic_type = f"output_topic_{team_id}"`; shared `_output_message_queue: asyncio.Queue`.

### Decisive source
```python
for participant, agent_type in zip(self._participants, self._participant_topic_types, strict=True):
    await ChatAgentContainer.register(runtime, type=agent_type, factory=...)
    # own topic (direct RPC) AND the shared broadcast topic
    await runtime.add_subscription(TypeSubscription(topic_type=agent_type, agent_type=agent_type))
    await runtime.add_subscription(TypeSubscription(topic_type=self._group_topic_type, agent_type=agent_type))
# manager additionally subscribes to its own topic, the group topic, AND the output topic
```

**Flow:** first run → lazy `_init(runtime)` registers N containers + 1 manager and lays down subscriptions → broadcasts go to `group_topic_*` (everyone incl. manager hears) → direct commands (`GroupChatRequestPublish`, reset/pause) go to personal topics → every chat event also published to `output_topic_*`, which ONLY the manager subscribes to; the manager relays them into the plain asyncio output queue consumed by `run_stream`.
**Invariant:** names need only be unique WITHIN a team (UUID suffix isolates teams sharing one outer runtime); the manager must never appear in `participant_topic_types` (:67 validation in the manager ctor) or it would answer its own speaker requests; embedded mode builds `SingleThreadedAgentRuntime(ignore_unhandled_exceptions=False)` — a swallowed background error would strand the run forever.
**Probe:** `python/packages/autogen-agentchat/tests/test_group_chat.py::test_round_robin_group_chat[embedded]` / `[single_threaded]` parametrics (same topology over external vs embedded runtime); `test_declarative_groupchats_with_config` pins provider strings.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "BaseGroupChat _init group_topic_type output_topic_type TypeSubscription", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt instance-scoped topic namespaces + the three-role subscription layout (self/broadcast/output-tap). Adapt topic naming to your bus's id scheme. Omit the external-runtime injection option unless you nest teams inside one process-wide bus.
