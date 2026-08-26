<!-- capsule-v2 -->
# Subscription registry rebuild — what breaks if you cache recipients per topic naively?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** How are topic→recipients mappings kept correct when subscriptions arrive after messages already flowed?

## Seen-topic set drives full rebuild on every mutation
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_runtime_impl_helpers.py` (`SubscriptionManager`, :32–79).
**Signature:** `async def add_subscription(self, subscription: Subscription) -> None` / `get_subscribed_recipients(self, topic: TopicId) -> List[AgentId]`.
**Data Shape:** Three fields: `_subscriptions: List[Subscription]`, `_seen_topics: Set[TopicId]`, `_subscribed_recipients: DefaultDict[TopicId, List[AgentId]]`. Duplicate detection uses `Subscription.__eq__` (id-or-pair semantics), NOT identity.

### Decisive source
```python
async def add_subscription(self, subscription: Subscription) -> None:
    if any(sub == subscription for sub in self._subscriptions):
        raise ValueError("Subscription already exists")
    self._subscriptions.append(subscription)
    self._rebuild_subscriptions(self._seen_topics)   # recompute EVERY seen topic

def _build_for_new_topic(self, topic: TopicId) -> None:
    self._seen_topics.add(topic)
    for subscription in self._subscriptions:
        if subscription.is_match(topic):
            self._subscribed_recipients[topic].append(subscription.map_to_agent(topic))
```

**Flow:** first publish on a topic → `get_subscribed_recipients` builds + caches that topic → later `add_subscription` raises on exact duplicate else wipes the cache and rebuilds all seen topics from scratch.
**Invariant:** recipient ORDER is subscription-registration order per topic (list append), so delivery order is deterministic given registration order; `TypeSubscription.__eq__` (:66) treats two subs equal when ids match OR `(agent_type, topic_type)` match — so re-registering the same logical wiring raises even across processes with fresh uuid ids.
**Probe:** `python/packages/autogen-core/tests/test_subscription.py::test_subscription_deduplication` (duplicate wiring rejected); `::test_type_subscription_match/map` (topic-type match maps source→agent key).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "SubscriptionManager rebuild subscribed_recipients is_match map_to_agent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt rebuild-on-mutation over incremental patching until subscription counts make it hot — correctness beats cleverness and the code stays 50 lines. Adapt equality semantics to your id scheme but KEEP the pair-equality fallback so logical duplicates fail loud. Omit prefix matching unless you need direct-message topics (next capsule).
