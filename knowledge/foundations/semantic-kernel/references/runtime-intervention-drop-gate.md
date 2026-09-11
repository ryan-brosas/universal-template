<!-- capsule-v2 -->
# Runtime intervention drop gate — pre-dispatch interception with per-arm failure asymmetry

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How do intervention handlers intercept, modify, or drop every message before dispatch — and what happens when a handler raises or returns None?

## InterventionHandler protocol + _process_next match arms
**Path/Symbol:** `python/semantic_kernel/agents/runtime/core/intervention.py:DropMessage` (lines 18–25), `InterventionHandler` (28–54), `DefaultInterventionHandler` (57–78); `in_process/in_process_runtime.py:_warn_if_none` (150–164), send arm (546–581), publish arm (583–619), response arm (623–648).
**Signature:** `async def on_send(self, message, *, message_context, recipient) -> Any | type[DropMessage]`; `async def on_publish(self, message, *, message_context) -> Any | type[DropMessage]`; `async def on_response(self, message, *, sender, recipient) -> Any | type[DropMessage]`.
**Data Shape:** `DropMessage` is a `@final` empty marker class; handlers may return the class itself OR an instance (`temp_message is DropMessage or isinstance(temp_message, DropMessage)` catches both). Returning the (possibly modified) message continues dispatch; `None` is treated as no-change with a RuntimeWarning.

### Decisive source
```python
# send arm — handler exception reaches the caller's future
temp_message = await handler.on_send(message, message_context=message_context, recipient=recipient)
_warn_if_none(temp_message, "on_send")
...
except BaseException as e:
    future.set_exception(e)
    return
if temp_message is DropMessage or isinstance(temp_message, DropMessage):
    ...
    future.set_exception(MessageDroppedException())
    return
message_envelope.message = temp_message

# publish arm — handler exception is logged and swallowed (fire-and-forget)
except BaseException as e:
    # TODO(evmattso): we should raise the intervention exception to the publisher.
    logger.error(f"Exception raised in in intervention handler: {e}", exc_info=True)
    return
```

**Flow:** Handlers run in `_process_next` BEFORE the envelope is spawned as a background task, sequentially in list order; each handler sees the previous handler's output (`message_envelope.message = temp_message` after each). Drop semantics per arm: send → caller's future gets `MessageDroppedException`; publish → silent return (no subscriber ever sees it); response → the awaiting caller's future gets `MessageDroppedException`. Failure asymmetry: on_send exception → `future.set_exception(e)` (caller sees it); on_publish exception → logged and swallowed (publishers cannot await); on_response exception → `future.set_exception(e)`. `_warn_if_none` issues a RuntimeWarning for a None return — you must return the message or DropMessage explicitly; None is never a drop.
**Invariant:** An intervention handler can never crash the runtime loop: every arm wraps the call in try/except and either defers the error to a future or logs it. A dropped send always surfaces as `MessageDroppedException` on the caller's future — never as silence.
**Probe:** No direct unit test file covers InterventionHandler/DropMessage in `python/tests/unit/` at this pin (grep for `InterventionHandler|DropMessage` in tests = 0 hits) — recorded evidence gap; the protocol is exercised indirectly by the runtime tests' happy paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "InterventionHandler DropMessage on_send on_publish on_response MessageDroppedException _warn_if_none", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the pre-dispatch interception point (all three traffic kinds, chained handler output, class-or-instance drop marker, None-is-not-a-drop warning) and the failure asymmetry (caller-visible on send/response, swallowed on publish). Adapt the marker to your host's exception or result type. Omit the `DefaultInterventionHandler` convenience subclass if your host composes handlers functionally.
