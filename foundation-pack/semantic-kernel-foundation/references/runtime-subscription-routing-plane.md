<!-- capsule-v2 -->
# Runtime subscription routing plane — topic-to-agent mapping, manager caching, and the auto prefix subscription

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How do topics map to agent instances, why does every registered agent get a prefix subscription, and how does the DefaultSubscription contextvar trick make cascades work?

## SubscriptionManager + Type/TypePrefix/Default subscriptions
**Path/Symbol:** `python/semantic_kernel/agents/runtime/in_process/runtime_impl_helpers.py:SubscriptionManager` (lines 40–94), `in_process/type_subscription.py:TypeSubscription` (whole, 67 ln), `in_process/type_prefix_subscription.py:TypePrefixSubscription` (whole, 67 ln), `in_process/default_subscription.py:DefaultSubscription` (27–46), `core/base_agent.py:register` (181–221).
**Signature:** `async def get_subscribed_recipients(self, topic: TopicId) -> list[AgentId]`; `def is_match(self, topic_id: TopicId) -> bool`; `def map_to_agent(self, topic_id: TopicId) -> AgentId`.
**Data Shape:** `SubscriptionManager` holds `_subscriptions: list[Subscription]`, `_seen_topics: set[TopicId]`, `_subscribed_recipients: DefaultDict[TopicId, list[AgentId]]` (cache). `TypeSubscription(topic_type, agent_type)`; `TypePrefixSubscription(topic_type_prefix, agent_type)`; `DefaultSubscription(topic_type="default", agent_type=None)` extends TypeSubscription.

### Decisive source
```python
# TypeSubscription: exact topic-type match; the topic SOURCE becomes the agent instance key
def is_match(self, topic_id: TopicId) -> bool:
    return topic_id.type == self._topic_type
def map_to_agent(self, topic_id: TopicId) -> AgentId:
    ...
    return CoreAgentId(type=self._agent_type, key=topic_id.source)

# TypePrefixSubscription: startswith match — the direct-message channel
def is_match(self, topic_id: TopicId) -> bool:
    return topic_id.type.startswith(self._topic_type_prefix)

# BaseAgent.register adds it automatically:
await runtime.add_subscription(
    TypePrefixSubscription(
        # The prefix MUST include ":" to avoid collisions with other agents
        topic_type_prefix=agent_type.type + ":",
        agent_type=agent_type.type,
    )
)

# SubscriptionManager caches per seen topic, rebuilds on any subscription change
async def get_subscribed_recipients(self, topic: TopicId) -> list[AgentId]:
    if topic not in self._seen_topics:
        self._build_for_new_topic(topic)
    return self._subscribed_recipients[topic]
```

**Flow:** `TypeSubscription.is_match` = exact topic-type equality; `map_to_agent` → `AgentId(agent_type, key=topic.source)` — the topic SOURCE becomes the agent instance key, so each source gets its own agent instance (state isolation per conversation; pinned by the "other namespace received 0" assertions). `TypePrefixSubscription` matches `startswith(prefix)` — `BaseAgent.register` auto-adds one with prefix `agent_type + ":"` so direct RPC-style sends (agent ids as topics) reach the agent without an explicit subscription; the colon prevents cross-agent prefix collisions. `DefaultSubscription`/`DefaultTopicId` resolve their missing agent_type/source from contextvars (`SubscriptionInstantiationContext` / `MessageHandlerContext`) — inside a handler, DefaultTopicId.source = the handling agent's key, which is what makes the cascade test's reply-to-same-topic loop converge. The manager caches recipients per seen TopicId and rebuilds the whole cache on any subscription add/remove; duplicate subscription (by `__eq__`) raises ValueError.
**Invariant:** A published message reaches exactly the agents whose subscriptions match the topic — one AgentId per matching subscription, sender excluded by the publish arm. The prefix subscription is additive infrastructure: removing it breaks direct sends but not topic pub-sub.
**Probe:** `python/tests/unit/agents/runtime/test_runtime.py::test_register_receives_publish` (line 175 — explicit TypeSubscription, other-key instance num_calls == 0), `test_default_subscription` (289), `test_default_subscription_publish_to_other_source` (339 — source="other" reaches the other-key instance only), `test_type_subscription` (314 — @type_subscription("Other")).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "TypeSubscription TypePrefixSubscription DefaultSubscription SubscriptionManager get_subscribed_recipients map_to_agent register", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: source-as-agent-key instance isolation, the auto-added colon-suffixed prefix subscription for direct sends, and the per-topic recipient cache with rebuild-on-change. Adapt the contextvar-based Default resolution to your host's ambient-context mechanism. Omit the DefaultSubscription class if your host requires explicit subscriptions everywhere.
