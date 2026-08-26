<!-- capsule-v2 -->
# ASGI response send loop — how are headers, cookies, streaming bodies and chunked plain bodies encoded onto the ASGI send channel?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** What is the exact message sequence a compliant ASGI HTTP response must emit, and how must sync iterators be consumed from async code?

## Response encoding onto ASGI messages
**Path/Symbol:** `django/core/handlers/asgi.py:ASGIHandler.send_response` (298–350) + `chunk_bytes` (352–367).
**Signature:** `async def send_response(self, response, send)`; `chunk_bytes(cls, data) -> Iterator[tuple[bytes, bool]]`.
**Data Shape:** headers as `(ascii-bytes name, latin1-bytes value)` tuples; cookies appended as extra `Set-Cookie` headers; body chunks of `chunk_size` (64 KiB) with `more_body` flags; FileResponse gets `block_size = chunk_size`.

### Decisive source
```python
for c in response.cookies.values():
    response_headers.append((b"Set-Cookie", c.OutputString().encode("ascii")))
await send({"type": "http.response.start", "status": response.status_code,
            "headers": response_headers})
if response.streaming:
    # Consume via __aiter__ ... Use aclosing() when consuming aiter.
    async with aclosing(aiter(response)) as content:
        async for part in content:
            for chunk, _ in self.chunk_bytes(part):
                await send({..., "more_body": True})
    await send({"type": "http.response.body"})       # empty final message
else:
    for chunk, last in self.chunk_bytes(response.content):
        await send({..., "body": chunk, "more_body": not last})
```
and `chunk_bytes`: empty data yields `(data, True)` once — the zero-length body still emits exactly one final `more_body=True→False`-style closing message.

**Flow:** collect headers (case-preserving: some non-RFC clients require e.g. exact `Content-Type`) → append one Set-Cookie per cookie → emit `http.response.start` exactly once → stream via `aiter()` (which maps sync iterators to async) wrapped in `aclosing()` for deterministic generator close → always terminate with an explicit empty final `http.response.body`.
**Invariant:** (1) Streaming responses ignore each chunk's own "last" flag and rely on the single empty closing message — mixing the two conventions corrupts framing. (2) `aclosing(aiter(response))` is mandatory so a mid-stream failure closes the underlying sync generator. (3) Header values encode ascii-name/latin1-value; cookie strings must survive ascii encoding.
**Probe:** `tests/asgi/tests.py::ASGITest.test_streaming` (:704), `.test_file_response` (:101), `.test_headers` (:182).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "send_response chunk_bytes http.response.start", limit: 10 });
```

## Verdict
Adopt the start-then-bodies-with-explicit-close framing for any ASGI-compatible sender; adapt encodings if your platform allows str headers; omit FileResponse block-size promotion if you lack file responses. Direct tests cited executed green at this pin.
