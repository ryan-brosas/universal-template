<!-- capsule-v2 -->
# WSGI file_wrapper close patch — how does a server-managed file response still get response.close() called?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** When the WSGI server takes over the response body via `wsgi.file_wrapper`, who is responsible for closing the HttpResponse and its resources?

## File-wrapper close handoff
**Path/Symbol:** `django/core/handlers/wsgi.py:WSGIHandler.__call__` (120–144).
**Signature:** `__call__(self, environ, start_response)` — final branch swaps `response.file_to_stream.close` before delegating to the platform wrapper.
**Data Shape:** Trigger condition: `response.file_to_stream` set (FileResponse with a real file) AND `environ["wsgi.file_wrapper"]` present. The wrapper result replaces the response object as the return value.

### Decisive source
```python
if getattr(response, "file_to_stream", None) is not None and environ.get(
    "wsgi.file_wrapper"
):
    # If `wsgi.file_wrapper` is used the WSGI server does not call
    # .close on the response, but on the file wrapper. Patch it to use
    # response.close instead which takes care of closing all files.
    response.file_to_stream.close = response.close
    response = environ["wsgi.file_wrapper"](
        response.file_to_stream, response.block_size
    )
return response
```

**Flow:** normal path: handler returns response; server calls its `.close()` → `request_finished` signal fires. File-wrapper path: server will call close on the WRAPPER, not the response → monkey-patch the file object's close to point at `response.close()` → return the wrapper so the server's own close call cascades into full resource release.
**Invariant:** (1) Resource-closer ownership moves with the body: whatever object the server closes must transitively invoke `HttpResponseBase.close()` (which drains `_resource_closers` and sends `request_finished`). (2) The patch happens BEFORE constructing the wrapper and mutates the shared file object — doing it after would leave a window where the server closes only the fd.
**Probe:** `tests/handlers/tests.py::SignalsTests.test_request_signals` (:176) + `.test_request_signals_streaming_response` (:182) pin that request_finished fires exactly once per served response including streaming; `tests/asgi/tests.py::ASGITest.test_untouched_request_body_gets_closed` (:356) pins the ASGI-side equivalent for unread bodies.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "WSGIHandler response streaming", limit: 10 });
```

## Verdict
Adopt the close-delegation patch whenever handing bodies to a platform-managed wrapper; adapt attribute names to your wrapper protocol; omit entirely if your server always closes the response object itself. Coverage caveat: the exact wrapper branch is pinned indirectly via signal-firing tests rather than a dedicated test — noted honestly.
