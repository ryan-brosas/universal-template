<!-- capsule-v2 -->
# Publish sender-skip + gather barrier — why doesn't a publisher hear itself, and what happens when one subscriber throws?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** How does fan-out prevent self-delivery, and how are concurrent subscriber failures contained?

## Identity-skip at delivery time; gather with per-handler re-raise
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py` (`_process_publish` :557–630).
**Signature:** `async def publish_message(self, message: Any, topic_id: TopicId, *, sender: AgentId | None = None, ...) -> None`.
**Data Shape:** Recipients resolved via `SubscriptionManager.get_subscribed_recipients(topic_id)`; each delivery wrapped in a local closure `_on_message(agent, message_context)` returning a coroutine collected into `responses: List[Awaitable[Any]]`; publish context sets `is_rpc=False`.

### Decisive source
```python
recipients = await self._subscription_manager.get_subscribed_recipients(message_envelope.topic_id)
for agent_id in recipients:
    # Avoid sending the message back to the sender
    if message_envelope.sender is not None and agent_id == message_envelope.sender:
        continue
...
future = _on_message(agent, message_context)     # NOT awaited here
responses.append(future)
await asyncio.gather(*responses)                 # first exception propagates
except BaseException as e:
    if not self._ignore_unhandled_handler_exceptions:
        self._background_exception = e           # surfaces on NEXT process_next
finally:
    self._message_queue.task_done()
```

**Flow:** dequeue → resolve recipients → skip the sender identity → create all delivery coroutines → gather → failures logged per-agent inside `_on_message` (which logs AND re-raises) → either swallowed (default `ignore_unhandled_exceptions=True`) or latched into `_background_exception`.
**Invariant:** skip compares FULL AgentId identity `(type, key)` — an agent only skips itself for this exact source key, so two instances of the same type still both receive the broadcast; the embedded agentchat runtime constructs with `ignore_unhandled_exceptions=False` (`_base_group_chat.py:141`) precisely because a silently-dead group chat is worse than a crash.
**Probe:** `python/packages/autogen-core/tests/test_runtime.py::test_event_handler_exception_propogates` and `::test_event_handler_exception_multi_message` (exception surfacing semantics); `::test_register_receives_publish_cascade` (fan-out chains).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "_process_publish get_subscribed_recipients ignore_unhandled_exceptions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt full-identity sender-skip (not type-skip) and the explicit choice of fail-loud vs fail-quiet as a CONSTRUCTOR flag, not a call-site afterthought. Adapt to structured concurrency (TaskGroups) if your host is 3.11+. Omit OTel span nesting inside `_on_message` unless tracing matters.
