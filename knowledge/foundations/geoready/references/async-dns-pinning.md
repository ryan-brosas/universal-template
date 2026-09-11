<!-- capsule-v2 -->
# Async pinning trap — why threading.local silently leaks DNS pins between coroutines

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How must DNS pinning change when the same fetch pipeline runs under asyncio?

## contextvars + threading.local dual-set
**Path/Symbol:** `src/geo_optimizer/utils/http_async.py:fetch_url_async` (46–120), `_pinning_ctx` (28–30).
**Signature:** `fetch_url_async(url, client=None, timeout=10, max_size=MAX_RESPONSE_SIZE) -> (response|None, error|None)`.
**Data Shape:** `_pinning_ctx: contextvars.ContextVar[dict | None]` mirrors the sync `_pinning_local` payload `{host, ip, port}`.

### Decisive source
```python
# Fix H-1: use contextvars instead of threading.local for async-safe DNS pinning.
# threading.local is per-thread, NOT per-coroutine. In asyncio, multiple coroutines
# share the same thread, so the last coroutine to set the pin before an await wins.
_pinning_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar("_pinning_ctx", default=None)
...
if _pinned_ip:
    pin_data = {"host": _parsed.hostname, "ip": _pinned_ip, "port": _target_port}
    # Set both: threading.local for the patched getaddrinfo, contextvar for safety
    _pinning_local.pin = pin_data
    _pinning_ctx.set(pin_data)
```

**Flow:** validate via `resolve_and_validate_url` → set BOTH the thread-local (the patched `socket.getaddrinfo` reads it synchronously inside urllib3's connect) and the ContextVar (per-task isolation) → httpx AsyncClient with `follow_redirects=False` → manual redirect loop revalidating each hop like the sync path.
**Invariant:** Under asyncio a bare thread-local pin is a CROSS-COROUTINE LEAK: coroutine A pins host X, awaits; coroutine B sets its own pin; A resumes and dials B's IP. The patched resolver only consults the thread-local, so the async path must still SET it — but scope-correct behavior requires the contextvar copy for anything reading identity across await points. A porter who "cleans this up" to contextvar-only breaks pinning entirely (resolver never sees it); one who keeps thread-local-only reintroduces the leak.
**Probe:** `tests/test_http_async.py` (async fetch + redirect revalidation suite; `PYTHONPATH=src pytest tests/test_http_async.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "_pinned_getaddrinfo thread-local", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the dual-set discipline whenever a synchronous global hook (socket/DNS) must serve an async caller pool; adapt storage to your runtime's task-local primitive; omit httpx specifics if your stack differs but keep manual-redirect revalidation.
