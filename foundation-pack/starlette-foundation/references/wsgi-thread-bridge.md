<!-- capsule-v2 -->
# WSGIMiddleware — sync WSGI app driven from async ASGI via memory streams

**Source:** Starlette BSD-3-Clause `main@675ae768` (DEPRECATED, points to a2wsgi); Codebase Memory `ext-starlette`. **Question:** What is the minimal correct bridge from a threaded WSGI callable into an async send channel?

## build_environ
**Path/Symbol:** `starlette/middleware/wsgi.py:build_environ` (:25-74).
**Data Shape:** utf8→latin1 roundtrip on SCRIPT_NAME/PATH_INFO (WSGI legacy encoding); body fully buffered into BytesIO BEFORE the app starts (no streaming input); duplicate headers joined with ","; content-length/content-type promoted to bare keys, rest HTTP_-prefixed upper-snake.
**Probe:** `tests/middleware/test_wsgi.py::test_build_environ` (:107).

## WSGIResponder — thread + stream choreography
**Path/Symbol:** `starlette/middleware/wsgi.py:WSGIResponder.__call__` (:100-114), `start_response` (:121-143), `wsgi` (:145-156).
### Decisive source
```python
async with create_collapsing_task_group() as task_group:
    task_group.start_soon(self.sender, send)          # async side: drains stream → ASGI send
    async with self.stream_send:
        await anyio.to_thread.run_sync(self.wsgi, environ, self.start_response)  # sync side
if self.exc_info is not None:
    raise self.exc_info[0].with_traceback(...)        # exc_info from start_response re-raised
```
**Flow:** the WSGI app runs IN A WORKER THREAD and pushes chunks via `anyio.from_thread.run(stream_send.send, ...)` — blocking-call-to-async-channel bridge; start_response captures status/headers once (subsequent calls only record exc_info per PEP 3333).
**Invariant:** exc_info argument to start_response is an ERROR SIGNAL, not metadata; ignoring it loses WSGI error propagation. Body messages are sent with more_body=True then a final empty body.
**Probe:** `::test_wsgi_exc_info` (:92), `::test_wsgi_exception` (:83).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "start_response", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "build_environ", limit: 5 });
```

## Verdict
Omit for new code (deprecated upstream in favor of a2wsgi) — but ADOPT the from_thread bridge + collapsing-group pattern whenever you must call blocking Python from async contexts. The environ builder is adaptable reference material.
