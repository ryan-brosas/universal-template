<!-- capsule-v2 -->
# Shared aiohttp session pool — How do you share one outbound HTTP session across a FastAPI monolith without leaking connections?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** How does a proxy-heavy backend reuse one aiohttp ClientSession for every provider call while guaranteeing per-response cleanup even when streaming is interrupted?

## Shared-pool seam (graph cluster 180/107 dependency)
**Path/Symbol:** `backend/open_webui/utils/session_pool.py:get_session` (53-82), with `cleanup_response` (94-115), `stream_wrapper` (118-138), `get_client_timeout` (49-50).
**Signature:** `async def get_session() -> aiohttp.ClientSession`; `async def cleanup_response(response: Optional[aiohttp.ClientResponse], session: Optional[aiohttp.ClientSession] = None)`; `async def stream_wrapper(response, session=None, content_handler=None, passthrough=False)`.
**Data Shape:** module-global `_session: Optional[ClientSession]`; env knobs `AIOHTTP_POOL_CONNECTIONS` / `AIOHTTP_POOL_CONNECTIONS_PER_HOST` / `AIOHTTP_POOL_DNS_TTL` where unset → `None`. Output: the shared session; streaming callers receive a generator that owns cleanup.

### Decisive source
```python
        if AIOHTTP_POOL_CONNECTIONS is not None:
            connector_kwargs['limit'] = AIOHTTP_POOL_CONNECTIONS
        else:
            connector_kwargs['limit'] = 0  # aiohttp: 0 = unlimited

        r = await session.request(...)
        if not r.ok: ... raise HTTPException(status_code=r.status, ...)
        if stream:
            streaming = True
            return StreamingResponse(
                stream_wrapper(r, passthrough=passthrough), ...)

    finally:
        if not streaming:
            await cleanup_response(r)
```
(ollama.py send_request shows the caller side; session_pool.py 62/66 show the unlimited default.)

```python
    """Wrap a stream to ensure cleanup happens even if streaming is interrupted.

    This is more reliable than BackgroundTask which may not run if the client
    disconnects.  When using the shared pool, ``session`` should be ``None``.
```

**Flow:** first caller → lazy-create TCPConnector (ttl_dns_cache, enable_cleanup_closed, limits; unset ⇒ unlimited) → shared session cached → every provider request borrows it → unary path cleans up in the request's own `finally`; streaming path transfers ownership to `stream_wrapper`, whose `finally` releases the response whenever iteration ends — normal completion, upstream error, or client disconnect.
**Invariant:** never close the shared session per-request (only app shutdown via `close_session()`); exactly ONE cleanup owner per response (request-finally XOR stream-wrapper finally, switched by the `streaming` flag); cleanup must tolerate both aiohttp<3.9 coroutine and ≥3.9 synchronous `close()` (`result = response.close(); if result is not None: await result`).
**Probe:** no upstream test files exist at this HEAD (standing caveat). Deterministic probe: `grep -n "0  # aiohttp: 0 = unlimited" backend/open_webui/utils/session_pool.py` → lines 64/68 (observed); `grep -n "more reliable than BackgroundTask" backend/open_webui/utils/session_pool.py` → line 121.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "shared aiohttp ClientSession pool get_session cleanup_response", limit: 10, fields: ["signature", "name", "file"] });
```
Executed this pass: resolves `utils.session_pool.get_session` 53-82, `cleanup_response` 94-115, `stream_wrapper` 118-138 as top hits.

## Verdict
Adopt: lazy singleton pool, unset-env⇒unlimited semantics, single-owner cleanup flag, version-tolerant close, finally-based stream cleanup instead of BackgroundTask. Adapt: env names and logging to host conventions. Omit: open-webui's specific `close_session()` wiring into app shutdown. Caveats: module docstring claims defaults 100/30/300 but code maps unset→unlimited — source wins; zero direct tests upstream. Disambiguation: `utils/misc.py` carries a TWIN pair for callers that create their OWN one-off sessions — `misc.cleanup_response` 1121-1136 / `misc.stream_wrapper(response, session, content_handler=None)` 1139-1149 (session argument REQUIRED there, optional here) plus `stream_chunks_handler` 1152-1214; grabbing the wrong wrapper silently changes who closes the session. Pool adoption is not universal either: openai.py `send_get_request` still builds a fresh `aiohttp.ClientSession` per call (:98) — only the request/stream plane uses the shared pool.
