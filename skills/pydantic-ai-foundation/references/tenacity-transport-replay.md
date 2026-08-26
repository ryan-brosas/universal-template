<!-- capsule-v2 -->
# Tenacity retry transport — how do you add retries to an HTTP client without the caller seeing them?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does a transport-level retry wrapper convert responses into exceptions and replay requests safely?

## tenacity-transport-replay
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/retries.py:` `RetryConfig` TypedDict (:72–134), `HTTPX2TenacityTransport` (:140–236), `AsyncHTTPX2TenacityTransport` (:239–339), deprecated `TenacityTransport`/`AsyncTenacityTransport` twins (:343–511).
**Signature:** `(config: RetryConfig, wrapped: httpx2.BaseTransport | None = None, validate_response: Callable[[httpx2.Response], object] | None = None)`; `handle_request(request) -> Response` decorates a per-request closure with `@retry(**self.config)`.
**Data Shape:** `RetryConfig` is EXACTLY the kwargs of tenacity's `retry` decorator (`sleep/stop/wait/retry/before/after/before_sleep/reraise/retry_error_cls/retry_error_callback`, all optional → tenacity defaults). Note tenacity defaults differ sharply from intuition: stop=stop_never, wait=wait_none.

### Decisive source
```python
def handle_request(self, request):
    @retry(**self.config)
    def handle_request(req):
        response = self.wrapped.handle_request(req)
        # this is normally set by httpx _after_ calling this function, but we want
        # the request in the validator:
        response.request = req
        if self.validate_response:
            try:
                self.validate_response(response)
            except Exception:
                response.close()      # async twin: await response.aclose()
                raise
        return response
    return handle_request(request)
```

**Flow:** caller passes config + optional validator → each request re-enters the decorated closure → wrapped transport runs → validator (typically `lambda r: r.raise_for_status()`) converts bad statuses into exceptions the controller can retry on → on validation failure the response is CLOSED BEFORE re-raising (connection-limit leak otherwise).
**Invariant:** three rules:
1. Set `response.request` manually before validating — the HTTP library only attaches it after the transport returns, and the validator/exceptions need it.
2. Close the failed response before propagating to the retry controller, or pooled connections leak per attempt.
3. Non-replayable streaming bodies cannot survive a retry: attempt 1 consumes the stream and attempt 2 raises `httpx2.StreamConsumed` (docstring contract :151–153) — retried requests need bytes-like bodies.
4. The decorator is built INSIDE `handle_request` per call (closure over `request`), so no shared mutable retry state exists between concurrent requests.
**Probe:** `tests/test_tenacity.py::TestHTTPX2TenacityTransport` (:42–135: passes-response-without-validator, retries-response-validator, exits-wrapped-transport-once), `TestWaitRetryAfter` (:479+); legacy twins warn with the httpx2 replacement (`TestLegacyHTTPXTransports` :137–158).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "HTTPX2TenacityTransport RetryConfig validate_response handle_async_request", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the transport-wrapper pattern (config-as-decorator-kwargs + manual request back-reference + close-before-reraise); adapt validator vocabulary to your stack; omit deprecated httpx twins.
