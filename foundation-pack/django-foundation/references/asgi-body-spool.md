<!-- capsule-v2 -->
# ASGI body spool + ThreadSensitiveContext — how do you buffer an unbounded upload stream without holding the event loop or exhausting memory?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** Where should request bodies spool between memory and disk, and why does each request run inside its own `ThreadSensitiveContext`?

## Spooled body reader with per-request thread-sensitivity
**Path/Symbol:** `django/core/handlers/asgi.py:ASGIHandler.read_body` (239–267) and `ASGIHandler.__call__`/`__init__` (157–173); `chunk_size = 2**16`, `body_receive_timeout = 60`.
**Signature:** `async def read_body(self, receive) -> tempfile.SpooledTemporaryFile`; `async def __call__(self, scope, receive, send)` wraps `handle` in `async with ThreadSensitiveContext()`.
**Data Shape:** SpooledTemporaryFile rolls to disk at `settings.FILE_UPLOAD_MAX_MEMORY_SIZE`; writes go inline while in-memory but hop threads (`thread_sensitive=False`) once rolled; disconnect mid-body closes the file and raises `RequestAborted`; final `seek(0)` before returning.

### Decisive source
```python
body_file = tempfile.SpooledTemporaryFile(
    max_size=settings.FILE_UPLOAD_MAX_MEMORY_SIZE, mode="w+b")
while True:
    message = await receive()
    if message["type"] == "http.disconnect":
        body_file.close()
        raise RequestAborted()
    if "body" in message:
        on_disk = getattr(body_file, "_rolled", False)
        if on_disk:
            async_write = sync_to_async(body_file.write, thread_sensitive=False)
            await async_write(message["body"])
        else:
            body_file.write(message["body"])
    if not message.get("more_body", False):
        break
body_file.seek(0)
```
and the entrypoint: every HTTP connection gets `async with ThreadSensitiveContext(): await self.handle(...)` — this is what gives `sync_to_async(thread_sensitive=True)` views their own dedicated thread per request instead of sharing a global pool.

**Flow:** allocate spool → loop receive → abort on disconnect (close first!) → write chunks (inline pre-roll, off-thread post-roll so slow disks never block the loop) → break on last chunk → rewind. The per-request `ThreadSensitiveContext` scopes Django's thread-sensitive executor so concurrent requests don't serialize behind one shared thread.
**Invariant:** (1) The roll-state check `_rolled` decides the write path per-chunk, not per-request — a single upload can straddle both paths. (2) Disconnect during body read must close the spool BEFORE raising, or fds leak on every abandoned upload. (3) One `ThreadSensitiveContext` per request is the unit of thread isolation; nesting handlers inside one context silently changes sync-view scheduling semantics.
**Probe:** `tests/asgi/tests.py::ASGITest.test_read_body_thread` (:739), `.test_post_body` (:213), `.test_request_lifecycle_signals_dispatched_with_thread_sensitive` (:471), `.test_concurrent_async_uses_multiple_thread_pools` (:524).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "read_body SpooledTemporaryFile ThreadSensitiveContext", limit: 10 });
```

## Verdict
Adopt spool-to-disk buffering with per-chunk roll detection for any streaming body receiver; adapt the max-size setting name and thread-pool primitives to your runtime; omit `ThreadSensitiveContext` only if you have no synchronous code that assumes per-request thread affinity. Direct tests cited executed green at this pin.
