<!-- capsule-v2 -->
# Config.load middleware stack — in what order are WSGI/ASGI2 adapters, tracing, and proxy headers wrapped, and why can't it change?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What is the exact wrap order applied to the user app inside `Config.load()`, and which steps mutate interface detection?

## Four-stage onion built at load time, once
**Path/Symbol:** `uvicorn/config.py:Config.load` (:495–541); interface sniffing :517–525; factory call convention :504–515.
**Signature:** `def load(self) -> None` (asserts `not self.loaded`; idempotence guard).
**Data Shape:** `self.loaded_app` mutates in place through each stage; final object is what every protocol instance receives as `config.loaded_app`.

### Decisive source
```python
# :504-513 — factory convention is CALL-THEN-CHECK, flag optional
try:
    self.loaded_app = self.loaded_app()
except TypeError as exc:
    if self.factory:
        logger.error("Error loading ASGI app factory: %s", exc)
        sys.exit(STARTUP_FAILURE)      # factory=True + real failure = hard exit
else:
    if not self.factory:
        logger.warning("ASGI app factory detected. Using it, but please consider setting the --factory flag explicitly.")
...
# :526-536 — wrap order is load-bearing
if self.interface == "wsgi":
    self.loaded_app = WSGIMiddleware(self.loaded_app); self.ws_protocol_class = None
elif self.interface == "asgi2":
    self.loaded_app = ASGI2Middleware(self.loaded_app)
if logger.getEffectiveLevel() <= TRACE_LOG_LEVEL:
    self.loaded_app = MessageLoggerMiddleware(self.loaded_app)
if self.proxy_headers:
    self.loaded_app = ProxyHeadersMiddleware(self.loaded_app, trusted_hosts=self.forwarded_allow_ips)
```

**Flow:** import-string resolution → SSL context build (with per-class `alpn_protocols`) → header pre-encoding → ws/lifespan class resolution → app import → factory probe (call it; TypeError only fatal when `--factory` was explicit; successful call without the flag logs a warning and keeps the result) → auto interface detection (class with `__await__`, function via `iscoroutinefunction`, else its `__call__`; non-coroutine ⇒ asgi2) → adapter wraps → trace logger wrap (only when uvicorn logger level ≤ TRACE=5) → ProxyHeaders wrap outermost. Protocols additionally apply FlowControl/limit_concurrency at request time — never here.
**Invariant:** Order is adapter-innermost → tracer → proxy-header-rewriter-outermost: ProxyHeaders must see the scope FIRST so inner apps receive corrected `client`/`scheme`; wrapping it inside the WSGI/ASGI2 adapter would feed raw values to legacy apps. The whole pipeline is computed once (`assert not self.loaded`); protocols lazily calling `config.load()` rely on that for cheap construction.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'MessageLoggerMiddleware(self.loaded_app)' uvicorn/uvicorn/config.py"` → 1; `bash -c "grep -cE 'self.loaded_app = (WSGIMiddleware|ASGI2Middleware)\(self.loaded_app\)' uvicorn/uvicorn/config.py"` → 2; `bash -c "grep -c 'ASGI app factory detected' uvicorn/uvicorn/config.py"` → 1.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"load config middleware proxy headers wsgi asgi2","limit":5,"detail":"ids"}` → resolves `Config.load` region line-exact (Method node spans the loader body).
**Verdict:** Adopt the wrap order and call-then-check factory convention verbatim. Adapt TRACE gating threshold to your logging framework. Omit the deprecation shim `setup_event_loop` raising AttributeError (:544–550).

