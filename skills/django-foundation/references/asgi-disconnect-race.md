<!-- capsule-v2 -->
# ASGI disconnect race — how do you serve a response while listening for client disconnect on the same receive channel?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** After the request body is fully read, the ASGI `receive` channel still carries `http.disconnect` — how does the handler race response delivery against client abandonment without leaking tasks or mis-signalling cancellation?

## TaskGroup race with sentinel exception
**Path/Symbol:** `django/core/handlers/asgi.py:ASGIHandler.handle` (175–218) + `listen_for_disconnect` (220–226).
**Signature:** `async def handle(self, scope, receive, send)`; inner: `async with asyncio.TaskGroup() as tg: tg.create_task(self.listen_for_disconnect(receive)); response = await self.run_get_response(request); await self.send_response(response, send); raise RequestProcessed`.
**Data Shape:** `RequestProcessed` is a locally-defined exception class used purely as a success sentinel; `listen_for_disconnect` raises `RequestAborted()` when it receives `http.disconnect`, else asserts on any other message type.

### Decisive source
```python
class RequestProcessed(Exception): pass
try:
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.listen_for_disconnect(receive))
            response = await self.run_get_response(request)
            await self.send_response(response, send)
            raise RequestProcessed
    except* (RequestProcessed, RequestAborted):
        pass
except BaseExceptionGroup as exception_group:
    if len(exception_group.exceptions) == 1:
        raise exception_group.exceptions[0]
    raise

if response is None:
    await signals.request_finished.asend(sender=self.__class__)
else:
    await sync_to_async(response.close)()
```

**Flow:** body read completes (disconnect during body read is already handled in `read_body`) → TaskGroup runs listener + request pipeline concurrently → happy path: response sent, raise `RequestProcessed` to cancel the still-pending listener → disconnect path: listener raises `RequestAborted`, group cancels/abandons the pipeline → unwrap singleton ExceptionGroups back to the bare exception so upstream handlers see normal exception types.
**Invariant:** (1) Success is signalled by raising, not by falling through — this is what cancels the listener; forgetting it wedges every subsequent request. (2) Only `(RequestProcessed, RequestAborted)` are swallowed at the `except*` level; any OTHER error re-raises as a group and single-member groups are unwrapped to preserve original tracebacks. (3) `response.close()` runs via `sync_to_async` AFTER the group exits — resource release must never be skipped by the disconnect path.
**Probe:** `tests/asgi/tests.py::ASGITest.test_disconnect` (:389), `.test_disconnect_both_return` (:397), `.test_delayed_disconnect_with_body` (:441) — pin all three interleavings of disconnect vs. completed response.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "listen_for_disconnect RequestProcessed TaskGroup", limit: 10 });
```

## Verdict
Adopt the sentinel-exception + TaskGroup race for any half-duplex protocol that keeps a control channel open after the body arrives; adapt `RequestAborted` to your abandonment signal; omit the ExceptionGroup unwrapping only if your callers tolerate groups (they usually don't). Direct tests cited executed green at this pin.
