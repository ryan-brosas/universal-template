<!-- capsule-v2 -->
# Http-client defaults plane — cached pooled clients, explicit-timeout honoring, refcount close gate, cookie isolation

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm` (MCP not connected at authoring time — direct source+test reading fallback, recorded in work record). **Question:** What timeout do the shared cached httpx clients get, how is client ownership tracked so a finalized handler never closes a client someone else still uses, and how are cookies kept from leaking between upstreams on a pooled client?

## Default timeouts — _DEFAULT_TIMEOUT vs _default_cached_client_timeout
**Path/Symbol:** `litellm/llms/custom_httpx/http_handler.py` — `_DEFAULT_TIMEOUT` (:134-137), `_default_cached_client_timeout` (:140-145); `get_configured_request_timeout` (request_timeout_resolver.py, sibling capsule router-timeout-resolution-chain).
**Signature:** `_default_cached_client_timeout() -> httpx.Timeout`.
**Data Shape:** `_DEFAULT_TIMEOUT = httpx.Timeout(timeout=COMPLETION_HTTP_FALLBACK_SECONDS  # 600, connect=HTTP_HANDLER_CONNECT_TIMEOUT_SECONDS  # 5)`; the configured variant keeps connect=5 and swaps only the read/pool/write timeout.

### Decisive source
```python
# http_handler.py:140-145
def _default_cached_client_timeout() -> httpx.Timeout:
    """Timeout for cached default httpx clients; honors an explicit litellm.request_timeout."""
    configured: Final = get_configured_request_timeout()
    if configured is None:
        return _DEFAULT_TIMEOUT
    return httpx.Timeout(timeout=configured, connect=HTTP_HANDLER_CONNECT_TIMEOUT_SECONDS)
```

**Flow:** `get_configured_request_timeout()` returns the explicit global ONLY when `request_timeout_explicitly_set` (the REQUEST_TIMEOUT env flag from the pass-4 timeout capsule) — so an unset global falls through to the shared 600s sentinel object (returned by identity, not copy). This closes the LIT-2369 hole: cached clients previously hardcoded 600s and never consulted an explicit `litellm.request_timeout`, so provider calls with no per-model timeout (e.g. Bedrock) hung for 600s.
**Invariant:** The identity of `_DEFAULT_TIMEOUT` when unconfigured is observable and tested (`is` comparison) — callers may rely on one shared Timeout object. An explicit global must reach CACHED clients, not just per-request kwargs.
**Probe:** `tests/test_litellm/llms/custom_httpx/test_http_handler.py::TestDefaultCachedClientTimeoutHonorsRequestTimeout` executed live at the pin → 3 passed (`test_default_when_request_timeout_unset` asserts `is _DEFAULT_TIMEOUT`; `test_uses_explicit_request_timeout` asserts read==300.0/connect==5.0; `test_cached_async_client_built_with_explicit_request_timeout` drives `get_async_httpx_client`).

## Cached-client pool + ownership + refcount close gate
**Path/Symbol:** `http_handler.py` — `get_async_httpx_client` (:1443-1494), `_get_httpx_client` (:1497-1540), `AsyncHTTPHandler.__init__`/`client` property (:542-579), `HTTPHandler.__init__`/`client` property (:1128-1182), `__del__` gates (:936-942 async, :1423-1428 sync), `_handler_may_close_client` (:151-160), `_CLIENT_REFCOUNT_WHEN_HANDLER_IS_SOLE_REFERRER = 2` (:148); TTL `_DEFAULT_TTL_FOR_HTTPX_CLIENTS = 3600` (constants.py:206).

### Decisive source
```python
# http_handler.py:151-160
def _handler_may_close_client(client_refcount: int, owns_client: bool) -> bool:
    """Only when the handler built the client and is still its sole referrer. Finalization
    proves that nothing references the *handler*; it proves nothing about the client, which
    a cached handler may have handed to consumers that outlive it. Callers must read the
    refcount at the call site, since binding the client to a parameter would inflate it."""
    return owns_client and client_refcount <= _CLIENT_REFCOUNT_WHEN_HANDLER_IS_SOLE_REFERRER
...
# http_handler.py:1423-1428 (sync __del__)
if _handler_may_close_client(sys.getrefcount(self._client), self._owns_client):
    self._client.close()
```

**Flow:** pool lookup keys are `"async_httpx_client"`/`"httpx_client"` + stringified params + provider, stored in `litellm.in_memory_llm_clients_cache` (an `LLMClientCache`, lazily created to avoid import-time globals) with TTL 3600s and `litellm_owned_client=True`. Handlers set `_owns_client=True` when they build their own client and False when one is injected via the `client` setter. The sync handler self-heals: its `client` property recreates a closed owned client under a double-checked lock. On finalization, `__del__` closes the client ONLY when `_handler_may_close_client(sys.getrefcount(self._client), self._owns_client)` — refcount ≤ 2 accounts for the getrefcount call itself plus the attribute reference, i.e. "sole referrer"; the refcount must be read at the call site because passing the client as a function argument would inflate it.
**Invariant:** Finalizing a handler proves nothing about the client's liveness — the close decision needs BOTH ownership AND sole-referrer status. Injected clients (setter path) are never closed by the handler. Self-heal applies only to owned clients.
**Probe:** same file — `test_sole_referrer_handler_may_close_but_a_sharing_one_may_not` executed live at the pin → passed (asserts all three gate combinations: (2, True)→True, (3, True)→False, (2, False)→False); the -k selection for this capsule ran 7 passed total.

## Cookie isolation on pooled clients
**Path/Symbol:** `http_handler.py` — `blocked_cookie_jar` (:163-169), httpx client construction (:608-617 async, :1156-1164 sync), aiohttp session factory (:1089-1094).

### Decisive source
```python
# http_handler.py:163-169
def blocked_cookie_jar() -> CookieJar:
    """A jar that stores no response cookie and sends none, for httpx clients.
    LiteLLM's outbound clients are pooled and shared by every caller, so a cookie one
    upstream sets would be replayed to every other upstream on a matching domain."""
    return CookieJar(policy=DefaultCookiePolicy(allowed_domains=()))
...
# http_handler.py:1092 — the aiohttp transport needs its own block
return ClientSession(connector=TCPConnector(**transport_connector_kwargs),
                     cookie_jar=DummyCookieJar(), trust_env=trust_env)
```

**Flow:** every httpx client (sync + async) is built with `cookies=blocked_cookie_jar()` — a jar whose policy allows zero domains, so it stores nothing and sends nothing. Because the DEFAULT transport is aiohttp (LiteLLMAiohttpTransport wraps a ClientSession with its own cookie jar invisible to httpx-level assertions), the session factory additionally passes `cookie_jar=DummyCookieJar()`.
**Invariant:** A pooled client shared across upstreams must be cookie-opaque at EVERY transport layer — blocking only the httpx jar leaves the leak intact on the aiohttp path.
**Probe:** same file — `test_sync_client_never_replays_one_upstreams_cookie_to_another` and `test_aiohttp_session_never_replays_one_upstreams_cookie_to_another` executed live at the pin → both passed (the latter asserts the real-path session jar IS a DummyCookieJar and stores nothing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "_default_cached_client_timeout _handler_may_close_client blocked_cookie_jar",
  filePattern: "http_handler.py", limit: 20 });
// → rank-1..n surface the timeout helper (:140), the refcount gate (:151), and the jar factory (:163)
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "get_async_httpx_client in_memory_llm_clients_cache ttl",
  filePattern: "http_handler.py", limit: 10 });
// → the pool lookup/store pair (:1443/:1497)
```

## Verdict
Adopt all four contracts: explicit-global-honoring default timeout with identity-preserved fallback object; param-keyed TTL pool with lazy cache creation; ownership flag + read-at-call-site refcount ≤ 2 close gate (never close injected clients; self-heal only owned ones); and cookie-opacity at both the httpx and underlying-transport layers. Adapt the TTL, key grammar, and connect/read split to your stack. Omit nothing structural. Coverage caveat: none — all three probe groups ran green at the pin.
