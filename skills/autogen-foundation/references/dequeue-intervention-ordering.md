<!-- capsule-v2 -->
# Dequeue-time intervention ordering — when do interception hooks run, and what does a Drop or handler exception cost the queue?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** At what point in the publish path does on_publish fire relative to recipient resolution and sender-skip, and which failure arms break queue accounting?

## Enqueue is clean; ALL interception happens after get() — and early returns skip task_done
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py` `publish_message` :387–429 (no hook), `_process_next` send arm :690–726 / publish arm :727–766 / response arm :767–791, `_process_publish` sender-skip :562–565 + `finally: task_done()` :628–629.
**Signature:** `async def _process_next(self) -> None` · hooks: `on_send(message, message_context, recipient)` / `on_publish(message, message_context)` / `on_response(message, sender, recipient)`.
**Data Shape:** handlers return `message | DropMessage | type[DropMessage]`; mutation is by envelope reassignment (`message_envelope.message = temp_message`) between successive handlers.

### Decisive source
```python
case PublishMessageEnvelope(...):                       # DEQUEUE time, not enqueue time
    if self._intervention_handlers is not None:
        for handler in self._intervention_handlers:
            try:
                temp_message = await handler.on_publish(message, message_context=message_context)
                _warn_if_none(temp_message, "on_publish")
            except BaseException as e:
                # TODO: we should raise the intervention exception to the publisher.
                logger.error(f"Exception raised in in intervention handler: {e}", exc_info=True)
                return                                   # <-- get() already consumed; NO task_done()
            if temp_message is DropMessage or isinstance(temp_message, DropMessage):
                event_logger.info(MessageDroppedEvent(...))
                return                                   # <-- same leak
            message_envelope.message = temp_message
    task = asyncio.create_task(self._process_publish(message_envelope))   # Drop never reaches recipients
```
```python
# inside _process_publish: skip and gather happen AFTER interception
if message_envelope.sender is not None and agent_id == message_envelope.sender:
    continue                                             # full AgentId identity skip, per recipient
...
finally:
    self._message_queue.task_done()
```

**Flow:** publisher enqueues with zero interception → dequeue → per-envelope arm runs handlers in order (mutating chain) → send/response arms funnel failures into the parked future (`set_exception(e)` for handler raise, `MessageDroppedException` for Drop) → publish arm logs-and-returns on handler exception (publisher NEVER learns; TODO admits it) and silently returns on Drop → survivors spawn delivery tasks whose own finally owes the task_done.
**Invariant:** ordering is fixed: intercept ⇒ drop/exception verdict ⇒ THEN recipient resolution ⇒ THEN per-recipient sender-skip. The asymmetry from the intervention-pipeline capsule holds, but the accounting caveat must be added: an intervention Drop or handler exception on ANY arm returns before any task_done for that already-consumed envelope, so `queue.join()`-based shutdown (`stop_when_idle`) can hang while such a message would have been in flight. Response-drop happens AFTER the receiving agent already ran.
**Probe:** `python/packages/autogen-core/tests/test_intervention.py::test_intervention_drop_send` (:62–83 — caller sees MessageDroppedException, agent num_calls==0), `::test_intervention_raise_exception_on_respond` (:134–157 — exception reaches the awaiting caller even though the agent already ran, num_calls==1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "autogen", qualified_name: "autogen.python.packages.autogen-core.src.autogen_core._single_threaded_agent_runtime.SingleThreadedAgentRuntime._process_publish" });
```

## Verdict
Adopt dequeue-time interception as the single choke point (one place to audit every crossing) with mutate-in-place chaining. Adapt which arms surface errors to callers — upstream's publish arm swallows them and says so in a TODO. Omit the naive join-based shutdown assumption: either call task_done on the early-return arms yourself, or make shutdown drain-count independent of interception outcomes.
