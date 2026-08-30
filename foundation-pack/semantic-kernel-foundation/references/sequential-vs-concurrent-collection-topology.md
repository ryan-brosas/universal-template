<!-- capsule-v2 -->
# Sequential vs concurrent collection topology — how each pattern collects results without a manager

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How do the sequential and concurrent orchestration patterns wire message topology and result collection, and why does sequential register actors in reverse?

## SequentialOrchestration / ConcurrentOrchestration
**Path/Symbol:** `python/semantic_kernel/agents/orchestration/sequential.py:SequentialAgentActor._handle_message` (lines 79–91), `_register_members` (154–177), `CollectionActor._handle_message` (110–115); `python/semantic_kernel/agents/orchestration/concurrent.py:ConcurrentOrchestration._start` (188–198), `CollectionActor._handle_message` (128–139), `_add_subscriptions` (216–226).
**Signature:** `async def _handle_message(self, message: SequentialRequestMessage, ctx: MessageContext) -> None`; `async def _register_members(self, runtime, internal_topic_type, exception_callback) -> None`; `async def _handle_message(self, message: ConcurrentResponseMessage, _: MessageContext) -> None`.
**Data Shape:** Wire messages: `SequentialRequestMessage(body: DefaultTypeAlias)` (request AND inter-agent hop AND final result), `ConcurrentRequestMessage(body: DefaultTypeAlias)`, `ConcurrentResponseMessage(body: ChatMessageContent)`. Actor types are `f"{agent.name}_{internal_topic_type}"`; collection type `f"CollectionActor_{internal_topic_type}"`.

### Decisive source
```python
# sequential.py — reverse registration so next_agent_type resolves at registration time
async def _register_members(self, runtime, internal_topic_type, exception_callback) -> None:
    next_actor_type = self._get_collection_actor_type(internal_topic_type)
    for agent in reversed(self._members):
        await SequentialAgentActor.register(
            runtime, self._get_agent_actor_type(agent, internal_topic_type),
            lambda agent=agent, next_actor_type=next_actor_type: SequentialAgentActor(
                agent, internal_topic_type, next_agent_type=next_actor_type, ...))
        next_actor_type = self._get_agent_actor_type(agent, internal_topic_type)

# sequential actor: invoke then forward to the NEXT actor (point-to-point, no pub/sub)
async def _handle_message(self, message: SequentialRequestMessage, ctx: MessageContext) -> None:
    response = await self._invoke_agent(additional_messages=message.body)
    target_actor_id = await self.runtime.get(self._next_agent_type)
    await self.send_message(SequentialRequestMessage(body=response), target_actor_id,
                            cancellation_token=ctx.cancellation_token)

# concurrent.py — one publish fans out; collection actor counts responses under a lock
async def _start(self, task, runtime, internal_topic_type, cancellation_token) -> None:
    await runtime.publish_message(ConcurrentRequestMessage(body=task),
                                  TopicId(internal_topic_type, self.__class__.__name__), ...)

async def _handle_message(self, message: ConcurrentResponseMessage, _: MessageContext) -> None:
    async with self._lock:
        self._results.append(message.body)
    if len(self._results) == self._expected_answer_count:
        if self._result_callback:
            await self._result_callback(self._results)
```

**Flow:** Sequential: `_start` sends `SequentialRequestMessage` to members[0]'s actor only; each actor
invokes its agent with the received body as `additional_messages`, then `send_message`s the response to the
next actor type; the LAST agent's next hop is the `CollectionActor`, whose handler is exactly
`result_callback(message.body)` — so the final result is the last agent's response, delivered once.
Registration is in REVERSE order because an actor's constructor needs `next_agent_type` as a plain string
resolved through `runtime.get` later — the loop seeds `next_actor_type` with the collection actor type and
walks backwards so each registration already knows its successor's type string. Concurrent: `_start` does ONE
`publish_message` to the internal topic; every member actor subscribed via `TypeSubscription` receives it,
invokes, and publishes a `ConcurrentResponseMessage` back; the `CollectionActor` (constructed with
`expected_answer_count=len(self._members)`) appends under `asyncio.Lock` and fires the callback exactly when
the count is reached — result is a LIST of all responses.
**Invariant:** Sequential is pure point-to-point `send_message` chaining with ZERO topic subscriptions
(test asserts `add_subscription.call_count == 0`); concurrent is pub/sub with one subscription per member
(`add_subscription.call_count == 2` for two members). The sequential result is a single message; the
concurrent result is a list of exactly `len(members)` messages. Actor-type names embed the internal topic
type so multiple orchestrations can share one runtime without collisions.
**Probe:** `python/tests/unit/agents/orchestration/test_sequential.py::test_prepare` (register counts 2+1, zero subscriptions), `test_invoke` (result is one ChatMessageContent), `test_invoke_with_agent_raising_exception`; `test_concurrent.py::test_prepare` (2+1 registers, 2 subscriptions), `test_invoke` (result is a list of 2), `test_invoke_cancel_before_completion` (`invoke_stream.call_count == 2` — both agents already started).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "SequentialAgentActor _register_members CollectionActor ConcurrentOrchestration publish_message expected_answer_count", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: reverse registration to make successor types resolvable at construction, point-to-point chaining for
sequential vs count-gated locked collection for concurrent, and topic-suffixed actor types for shared
runtimes. Adapt the runtime primitives (`runtime.get`, `send_message`, `publish_message`, TypeSubscription)
to your host's actor transport. Omit the streaming-callback plumbing if your port has no streaming surface.
