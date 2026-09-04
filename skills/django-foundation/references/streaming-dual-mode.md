<!-- capsule-v2 -->
# StreamingHttpResponse dual-mode iteration — how does one streaming class serve both sync and async consumers without deadlocking the event loop?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** When the content iterator's sync/async nature is unknown until assignment, how must consumption adapt, and what happens when the wrong protocol is used?

## Iterator-kind latching + cross-mode bridging
**Path/Symbol:** `django/http/response.py:StreamingHttpResponse` — `_set_streaming_content` (506–515), `streaming_content` property (487–500), `__iter__` (517–535), `__aiter__` (537–551).
**Signature:** `_set_streaming_content(self, value)`; `is_async` attribute latches the kind; `getvalue()` deliberately joins the generator.
**Data Shape:** sync iterables → `self._iterator = iter(value)`, `is_async=False`; TypeError on `iter()` ⇒ async iterable → `aiter(value)`, `is_async=True`; closeable sources appended to `_resource_closers`.

### Decisive source
```python
def _set_streaming_content(self, value):
    # Ensure we can never iterate on "value" more than once.
    try:
        self._iterator = iter(value)
        self.is_async = False
    except TypeError:
        self._iterator = aiter(value)
        self.is_async = True
    if hasattr(value, "close"):
        self._resource_closers.append(value.close)

def __iter__(self):                      # sync consumer of async content
    try:
        return iter(self.streaming_content)
    except TypeError:
        warnings.warn("StreamingHttpResponse must consume asynchronous "
                      "iterators ... Use a synchronous iterator instead.", ...)
        async def to_list(_iterator):
            as_list = []
            async for chunk in _iterator: as_list.append(chunk)
            return as_list
        return map(self.make_bytes, iter(async_to_sync(to_list)(self._iterator)))
```
The async property path wraps with an `awrapper()` generator applying `make_bytes` per part; the sync path uses `map(self.make_bytes, self._iterator)`.

**Flow:** assignment latches iterator kind ONCE (later reassignment can flip it; the property captures `_iterator` by lexical scope for that reason) → sync consumers of async content drain via `async_to_sync(to_list)` and WARN; async consumers of sync content drain via `sync_to_async(list)` and WARN — both degrade instead of raising.
**Invariant:** (1) The kind latch happens at construction, so handlers can branch on `response.is_async` before choosing send strategies. (2) Cross-mode consumption always buffers whole-content (list) before mapping — a naive incremental bridge would deadlock the loop. (3) Streaming content must be single-consumption by design (`Ensure we can never iterate on "value" more than once`); `getvalue()` joins and therefore exhausts.
**Probe:** `tests/asgi/tests.py::ASGITest.test_asyncio_streaming_cancel_error` (:629), `.test_streaming` (:704); `tests/handlers/tests.py::HandlerRequestTests.test_streaming` (:263) + `.test_async_streaming` (:268).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "_set_streaming_content is_async aiter streaming_content", limit: 10 });
```

## Verdict
Adopt kind-latching plus buffered cross-mode bridges for any dual-protocol streaming abstraction; adapt the warning policy to your deprecation strategy; omit getvalue() support if unbounded streams are legal in your system. Direct tests cited executed green at this pin.
