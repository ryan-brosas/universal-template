<!-- capsule-v2 -->
# SSE keepalive producer — How do idle SSE streams stay alive without blocking or leaking the generator?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** Why is a two-stage anyio memory-stream pipeline used instead of wrapping generator iteration in a timeout, and what does each stage own?

## Producer → keepalive → consumer pipeline
**Path/Symbol:** `fastapi/routing.py:_sse_producer_cm` (558–616) + `_sse_with_checkpoints` (621–629); wire format in `fastapi/sse.py:format_sse_event` (165–233), `KEEPALIVE_COMMENT = b": ping\n\n"`, `_PING_INTERVAL = 15.0` (237–241).
**Signature:** `_sse_producer_cm() -> AsyncIterator[ObjectReceiveStream[bytes]]` entered on the REQUEST exit stack; `format_sse_event(*, data_str, event, id, retry, comment) -> bytes`.
**Data Shape:** two `anyio.create_memory_object_stream[bytes](max_buffer_size=1)` channels: producer→keepalive and keepalive→response.

### Decisive source
```python
                    async def _producer() -> None:
                        async with send_stream:
                            async for raw_item in sse_aiter:
                                await send_stream.send(_serialize_sse_item(raw_item))

                    async def _keepalive_inserter() -> None:
                        async with send_keepalive, receive_stream:
                            try:
                                while True:
                                    try:
                                        with anyio.fail_after(_PING_INTERVAL):
                                            data = await receive_stream.receive()
                                        await send_keepalive.send(data)
                                    except TimeoutError:
                                        await send_keepalive.send(KEEPALIVE_COMMENT)
                            except anyio.EndOfStream:
                                pass
```

**Flow:** producer pulls/validates/serializes items independently of any timer — so `fail_after` NEVER wraps the generator's `__anext__`, avoiding CancelledError injection that would finalize user generators (and impossible for sync generators running in threads) → keepalive stage forwards bytes and emits `: ping` whenever 15s pass silently → response iterates via `_sse_with_checkpoints`, which awaits `anyio.sleep(0)` after EVERY yield so cancellation is deliverable even when the producer outpaces the client (PEP-789-style structured teardown: the CM's `tg.cancel_scope.cancel()` runs from the request exit stack, not GeneratorExit).
**Invariant:** (1) The CM must be entered on `async_exit_stack` (request scope) so teardown happens after streaming completes; entering it on a shorter-lived stack kills streams mid-flight. (2) `ServerSentEvent.raw_data` bypasses JSON encoding while plain data is ALWAYS JSON-quoted (`data: "hello"`); `data` XOR `raw_data` enforced by model validator. (3) Wire format ends `\n\n`; multi-line payloads split into repeated `data:` lines.
**Probe:** `tests/test_sse.py:test_keepalive_ping_async` / `test_keepalive_ping_sync` (monkeypatch `_PING_INTERVAL=0.05`, assert `": ping\n"` between two data events) and `test_no_keepalive_when_fast`.
