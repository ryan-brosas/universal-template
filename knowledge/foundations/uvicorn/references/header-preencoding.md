<!-- capsule-v2 -->
# Header pre-encoding and Server-header injection — why are custom headers lowercased latin-1 at load time?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** How do CLI `--header` pairs become wire bytes, and when is `server: uvicorn` prepended vs suppressed?

## One-time encode in Config.load; default_headers assembled per second
**Path/Symbol:** `uvicorn/config.py:Config.load` (:538–541); consumer `uvicorn/server.py:Server.on_tick` (:266–273).
**Signature:** `encoded_headers = [(key.lower().encode("latin1"), value.encode("latin1")) for key, value in self.headers]`.
**Data Shape:** `self.headers: list[tuple[str,str]]` (str world) → `self.encoded_headers: list[tuple[bytes,bytes]]` (wire world); `server_state.default_headers: list[tuple[bytes,bytes]]`.

### Decisive source
```python
# config.py :538-541
encoded_headers = [(key.lower().encode("latin1"), value.encode("latin1")) for key, value in self.headers]
self.encoded_headers = (
    [(b"server", b"uvicorn")] + encoded_headers
    if b"server" not in dict(encoded_headers) and self.server_header
    else encoded_headers
)
```
```python
# server.py on_tick :266-273 — Date header refreshed once/second from the tick loop
if counter % 10 == 0:
    current_time = time.time()
    current_date = formatdate(current_time, usegmt=True).encode()
    if self.config.date_header:
        date_header = [(b"date", current_date)]
    else:
        date_header = []
    self.server_state.default_headers = date_header + self.config.encoded_headers
```

**Flow:** user headers (CLI splits on FIRST colon: `--header "X: y"` → `["X", " y"]`) → lowercase + latin-1 encode ONCE at load → stored as bytes. Every second (tick counter % 10) the shared `default_headers` list is REBUILT as `[date?] + encoded_headers`; protocols snapshot this list per request cycle (`default_headers=self.server_state.default_headers`) so responses never format dates themselves.
**Invariant:** The `b"server" not in dict(encoded_headers)` check means a USER-supplied `Server:` header suppresses uvicorn's own — dedup by exact lowercase name, no second occurrence ever sent. latin-1 (not utf-8) matches HTTP header byte semantics; encoding failures surface at startup, not per-request.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'b\\"server\\" not in dict(encoded_headers)' uvicorn/uvicorn/config.py"` → 1; `bash -c "grep -c 'date_header' uvicorn/uvicorn/server.py"` ≥ 2 (config flag + rebuild branch). Behavioral pins: `tests/test_default_headers.py` (whole suite) and `tests/protocols/test_websocket.py:test_no_date_header` :1282.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"default headers date header encoded","limit":5,"detail":"ids"}` → resolves `on_tick` and `tests.test_default_headers` line-exact.
**Verdict:** Adopt load-time pre-encoding + periodic default-headers rebuild verbatim (it removes per-response strftime cost). Adapt the 1s cadence to your event loop budget. Omit ANSI color extras.

