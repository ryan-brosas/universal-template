<!-- capsule-v2 -->
# Envelope queue runtime — how do RPC sends get answers and publishes stay fire-and-forget?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory `ext-autogen`. **Question:** How does a single asyncio queue drive both direct sends (with responses) and topic publishes (without), without deadlocking `join()`?

## Single queue, three envelopes, one dispatcher
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py` (`SingleThreadedAgentRuntime.send_message` :332–385, `_process_send` :466–555, `_process_next` :671–794).
**Signature:** `async def send_message(self, message: Any, recipient: AgentId, *, sender: AgentId | None = None, cancellation_token: CancellationToken | None = None, message_id: str | None = None) -> Any`.
**Data Shape:** Three envelope dataclasses share one `Queue`: `SendMessageEnvelope{message, sender, recipient, future, cancellation_token, metadata, message_id}`, `PublishMessageEnvelope{message, cancellation_token, sender, topic_id, ...}`, `ResponseMessageEnvelope{message, future, sender, recipient, ...}`. The caller's answer arrives by resolving the future inside a later queue turn, not inline.

### Decisive source
```python
# send_message: enqueue then await the future resolved by a LATER queue turn
await self._message_queue.put(SendMessageEnvelope(...))
cancellation_token.link_future(future)
return await future

# _process_next: one dispatch turn spawns delivery as a BACKGROUND task
case SendMessageEnvelope(message=message, sender=sender, recipient=recipient, future=future):
    if self._intervention_handlers is not None:
        ...
    task = asyncio.create_task(self._process_send(message_envelope))
    self._background_tasks.add(task)
    task.add_done_callback(self._background_tasks.discard)
...
# Yield control to the message loop to allow other tasks to run
await asyncio.sleep(0)
```

**Flow:** caller creates future → enqueue `SendMessageEnvelope` → dispatcher dequeues → intervention pass → spawn `_process_send` background task → handler runs under `MessageHandlerContext.populate_context(recipient)` → enqueue `ResponseMessageEnvelope` → next dequeue resolves the future (`_process_response` :632–662) → caller wakes.
**Invariant:** every dequeue path must reach exactly one `task_done()` (:515 cancel arm, :526 handler-exception arm, :555 send success, :629 publish finally, :662 response) or `stop_when_idle`'s `queue.join()` blocks forever; publishes are RPC-less — `_process_publish` awaits `asyncio.gather(*responses)` but discards values, and an unhandled publish-handler exception only sets `self._background_exception` when `ignore_unhandled_exceptions=False`, re-raised at the NEXT `_process_next` entry (:674–678) after shutting the queue down.
**Probe:** `python/packages/autogen-core/tests/test_intervention.py::test_intervention_drop_send` (send raises `MessageDroppedException`, recipient `num_calls == 0`); `tests/test_runtime.py::test_event_handler_exception_propogates` pins the deferred background-exception surface.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "SingleThreadedAgentRuntime _process_next SendMessageEnvelope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-queue/envelope/background-task shape plus the strict task_done pairing rule for any in-process agent bus. Adapt envelope fields to your host (trace metadata optional). Omit the OpenTelemetry attribute plumbing unless you already run OTel.
