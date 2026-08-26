<!-- capsule-v2 -->
# RPC cancellation & failure ladder — where must a runtime guard future resolution against an already-cancelled token?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** How does synchronous cancellation interact with async future resolution, and where do RPC failures surface?

## Sync-lock token, guarded resolution arms, dispatch-time recipient failure
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_cancellation_token.py` `CancellationToken` :6–46; `python/packages/autogen-core/src/autogen_core/_single_threaded_agent_runtime.py` `send_message` :332–385, `_process_send` :466–555, `_process_response` :632–662.
**Signature:** `def link_future(self, future: Future[Any]) -> Future[Any]` · `async def send_message(self, message, recipient: AgentId, *, sender=None, cancellation_token=None, message_id=None) -> Any`.
**Data Shape:** token = bool + callback list under a `threading.Lock`; RPC = `SendMessageEnvelope{message, recipient, future, cancellation_token}` on the shared queue; resolution = `set_result`/`set_exception` on the caller's future.

### Decisive source
```python
# _cancellation_token.py — cancel() is idempotent; late callbacks fire immediately
def add_callback(self, callback):
    with self._lock:
        if self._cancelled: callback()
        else: self._callbacks.append(callback)

def link_future(self, future):
    with self._lock:
        if self._cancelled: future.cancel()
        else: self._callbacks.append(lambda: future.cancel())
    return future
```
```python
# send_message :363-366,379-380 — unknown recipient fails AT DISPATCH TIME, before queuing
future = asyncio.get_event_loop().create_future()
if recipient.type not in self._known_agent_names:
    future.set_exception(Exception("Recipient not found"))
    return await future
...
await self._message_queue.put(SendMessageEnvelope(...))
cancellation_token.link_future(future)
return await future
```
```python
# _process_send :512-514 and _process_response :660-661 — THE guards
except CancelledError as e:
    if not message_envelope.future.cancelled():   # token.link_future may have killed it already
        message_envelope.future.set_exception(e)
    self._message_queue.task_done(); return
...
if not message_envelope.future.cancelled():
    message_envelope.future.set_result(message_envelope.message)
self._message_queue.task_done()
```

**Flow:** caller creates future → unknown recipient ⇒ immediate exception · envelope queued, THEN `link_future` (mid-flight cancel kills the awaited future directly) · handler runs under `MessageHandlerContext.populate_context` · handler `CancelledError` ⇒ set_exception ONLY if the future survived the token · other `BaseException` ⇒ `set_exception` unguarded · success re-enqueues `ResponseMessageEnvelope` onto the SAME queue (single serialization point; on_response interventions run there) ⇒ guarded `set_result`.
**Invariant:** never call `set_result`/`set_exception` on a future the token may already have cancelled — both resolution arms test `future.cancelled()` first; cancel() is synchronous and idempotent (safe from any thread); RPC failures reach the awaiting caller, never a log-only path.
**Probe:** `python/packages/autogen-core/tests/test_cancellation.py::test_cancellation_with_token` (:65–87 — `token.cancel()` while the handler is mid-await ⇒ awaiter raises `CancelledError`; the agent instance observed BOTH `called` and `cancelled`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ qualified_name: "autogen.python.packages.autogen-core.src.autogen_core._cancellation_token.CancellationToken", project: "autogen" });
```

## Verdict
Adopt the sync-lock cancellation token, link-after-enqueue ordering, and cancelled()-guarded resolution arms verbatim for any RPC-over-queue runtime. Adapt the exception taxonomy (`MessageDroppedException`, recipient lookup) to your error types. Omit the OTel trace blocks and event logging around each arm.