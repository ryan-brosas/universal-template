<!-- capsule-v2 -->
# Intervention pipeline — where does message interception run, and what happens on None/DropMessage/raise?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** How do you intercept/drop messages centrally without agents knowing, and why do the three interception points behave differently on failure?

## Dispatch-time interception ladder
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py` (`_process_next` :689–791; helper `_warn_if_none` :132–146).
**Signature:** `InterventionHandler.on_send(message, *, message_context, recipient) -> MessageType | type[DropMessage]`; siblings `on_publish(message, *, message_context)`, `on_response(message, *, sender, recipient)`.
**Data Shape:** Handlers run in list order inside the dispatcher BEFORE any delivery task is spawned; returning the class `DropMessage` or an instance drops; returning `None` proceeds but emits a `RuntimeWarning` ("returned None. This might be unintentional"); a mutated return replaces `message_envelope.message`.

### Decisive source
```python
temp_message = await handler.on_send(message, message_context=message_context, recipient=recipient)
_warn_if_none(temp_message, "on_send")
except BaseException as e:
    future.set_exception(e)          # on_send failure -> caller sees it
    return
if temp_message is DropMessage or isinstance(temp_message, DropMessage):
    ...
    future.set_exception(MessageDroppedException())
    return                            # NOTE: skips remaining handlers AND task_done()
message_envelope.message = temp_message
```

**Flow:** on_send → mutate-or-drop → spawn `_process_send`; on_publish identical except handler exceptions are only logged (TODO comment admits the publisher never learns) and a drop just returns; on_response intercepts the reply path before the future resolves.
**Invariant:** a drop or handler exception on send/response returns WITHOUT calling `task_done()`, so an in-flight `queue.join()` still counts that envelope — drop semantics intentionally leave the queue unfinished while the awaiting caller gets its exception; publish-side failures are swallowed by design because no caller future exists.
**Probe:** `python/packages/autogen-core/tests/test_intervention.py::test_intervention_drop_send` / `::test_intervention_drop_response` / `::test_intervention_raise_exception_on_send` (exception type propagates to the awaiting caller).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "InterventionHandler on_send DropMessage MessageDroppedException", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-point interception taxonomy (request / broadcast / response) with mutate-in-place semantics and explicit-DropMessage sentinel. Adapt the warning-on-None policy to your logging conventions. Omit publish-side swallow behavior if your bus has backpressure callers that must learn about drops.
