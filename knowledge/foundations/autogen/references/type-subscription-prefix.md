<!-- capsule-v2 -->
# TypeSubscription keying + prefix direct-mail — how do topics route to agent instances, and how does an agent receive direct messages over pub/sub?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** What does `topic source` mean for agent identity, and why must the direct-message topic prefix contain a colon?

## Source-becomes-key subscription; prefix trick for point-to-point
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_type_subscription.py:53–66`; `python/packages/autogen-core/src/autogen_core/_base_agent.py` (`register` :214–254, `register_instance` :164–212).
**Signature:** `TypeSubscription(topic_type: str, agent_type: str | AgentType)`; `await MyAgent.register(runtime, type: str, factory, *, skip_class_subscriptions=False, skip_direct_message_subscription=False) -> AgentType`.
**Data Shape:** `is_match`: `topic_id.type == self._topic_type`. `map_to_agent`: `AgentId(type=self._agent_type, key=topic_id.source)` — the topic's source string becomes the agent instance key, giving one instance per source (multi-tenant by construction). Registration additionally wires a `TypePrefixSubscription(topic_type_prefix=agent_type.type + ":", agent_type=...)`.

### Decisive source
```python
def map_to_agent(self, topic_id: TopicId) -> AgentId:
    if not self.is_match(topic_id):
        raise CantHandleException("TopicId does not match the subscription")
    return AgentId(type=self._agent_type, key=topic_id.source)

# register(): direct messages ride a PREFIX subscription
await runtime.add_subscription(TypePrefixSubscription(
    # The prefix MUST include ":" to avoid collisions with other agents
    topic_type_prefix=agent_type.type + ":",
    agent_type=agent_type.type,
))
```

**Flow:** publish to `(type=T, source=S)` → matching TypeSubscription maps to `AgentId(T, S)` → runtime lazily instantiates that exact instance via factory → handler runs with per-source state isolation. Direct-to-agent publishes use topic type `"<agent_type>:<anything>"`, matched only by the colon-terminated prefix.
**Invariant:** without the colon, agent type `"writer"` would swallow topics of agent type `"writer_reviewer"` (prefix is a raw string match); `skip_class_subscriptions=True` drops the decorator-declared subscriptions but keeps the prefix sub only in `register_instance` (where it is default True) — flipping these flags silently changes who receives broadcasts.
**Probe:** `python/packages/autogen-core/tests/test_subscription.py::test_non_default_default_subscription` and `::test_skipped_class_subscriptions` (flag flips change recipient sets); `tests/test_runtime.py::test_default_subscription_publish_to_other_source` pins distinct sources → distinct instances.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "TypeSubscription map_to_agent TypePrefixSubscription skip_direct_message_subscription", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt "source = tenant/instance key" as the namespace discipline and the colon-sentinel prefix for point-to-point-over-broadcast. Adapt key derivation if your ids are structured objects. Omit `DefaultSubscription`'s contextvar-based agent-type detection (a registration-time convenience, `_default_subscription.py:20–29`) if you always name subscriptions explicitly.
