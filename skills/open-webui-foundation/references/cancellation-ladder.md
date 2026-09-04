<!-- capsule-v2 -->
# Stream cancellation ladder — what must happen when a client cancels mid-stream so nothing leaks upstream or corrupts persisted state?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** On `asyncio.CancelledError` during a streamed chat response, how do I release the provider connection, persist a consistent partial state, and still honor cancellation?

## Shielded cleanup, then honest re-raise
**Path/Symbol:** `backend/open_webui/utils/middleware.py` `except asyncio.CancelledError:` arm of `response_handler` (5554-5591).
**Signature:** handler body inside `try: ... outlets/background ... except asyncio.CancelledError: ... raise`.
**Data Shape:** `response.body_iterator` (upstream async generator); `output` (OR-style items accumulated so far); `metadata['chat_id']`/`['message_id']`; `ENABLE_REALTIME_CHAT_SAVE` env flag.

### Decisive source
```python
except asyncio.CancelledError:
    log.warning('Task was cancelled!')

    # Close the response body iterator to trigger cleanup
    # in stream_wrapper's finally block and release the
    # upstream connection.  Without this, the async
    # generator is orphaned and may spin in anyio internals.
    if hasattr(response, 'body_iterator') and hasattr(response.body_iterator, 'aclose'):
        try:
            await asyncio.shield(response.body_iterator.aclose())
        except (asyncio.CancelledError, Exception):
            pass
    ...
    try:
        await asyncio.shield(save_cancelled_state())
    except (asyncio.CancelledError, Exception):
        pass
    raise  # re-raise CancelledError for proper propagation
```
(middleware.py 5554-5591)

**Flow:** cancel observed → `asyncio.shield(body_iterator.aclose())` runs the upstream generator's `finally` so the HTTP connection is released (the source comment records the failure mode it prevents: an orphaned async generator spinning inside anyio) → shielded `save_cancelled_state()` emits `chat:tasks:cancel` and persists `{'done': True}` plus the partial `output` — with a split by save mode: without realtime save, upsert full `done+output`; WITH realtime save, rows already stream-persisted, so only `{'done': True}` with `touch=False` (do not bump the chat's updated-at timestamp for a cancellation) → re-raise CancelledError.
**Invariant:** every await between catching and re-raising is wrapped in `asyncio.shield`, because a second cancellation during cleanup must not abort the persistence half-done; both shielded steps swallow secondary exceptions (`except (CancelledError, Exception): pass`) — cleanup is best-effort, propagation is not. The ladder always ends in `raise`: the task still dies as cancelled.
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "await asyncio.shield(response.body_iterator.aclose())" backend/open_webui/utils/middleware.py` → 5563; `grep -n "await asyncio.shield(save_cancelled_state())" backend/open_webui/utils/middleware.py` → 5588; `grep -n "raise  # re-raise CancelledError" backend/open_webui/utils/middleware.py` → 5591.

## Get live surrounding code
**Retrieve:** the ladder lives inline in `streaming_chat_response_handler`'s except arm — free-text on its comment wording MISSES the graph (observed: drifts to `tasks.py`/state helpers). Target the enclosing handler:
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "streaming_chat_response_handler tool call iterations while loop", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves `streaming_chat_response_handler` 3750-5653; read lines 5554-5591 from source.

## Verdict
Adopt the three-step ladder verbatim as a shape: shielded upstream close → shielded idempotent state persist honoring your own realtime-save mode (`touch=False` semantics included) → unconditional re-raise. Adapt which resources need releasing and how "partial" state persists in your store. Omit the specific event name and Chats model. Coverage caveat: middleware.py is graph-clean but has no upstream test; claims pinned by direct source reads at lines cited above.
