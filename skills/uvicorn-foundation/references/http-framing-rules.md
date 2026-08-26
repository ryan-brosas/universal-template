<!-- capsule-v2 -->
# Response framing rules — when is chunked encoding auto-added, and what closes the connection?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** Given an app that sends neither Content-Length nor Transfer-Encoding, what does the server frame, and which app headers override keep-alive?

## Neither-declared ⇒ chunked (except HEAD/204/304); connection:close in response kills keep-alive
**Path/Symbol:** `uvicorn/protocols/http/httptools_impl.py:RequestResponseCycle.send` (:437–551) — framing scan :462–477, auto-chunk :514–517, completion :530–540.
**Signature:** `async def send(self, message: ASGISendEvent) -> None` with state machine `response_started/response_complete/chunked_encoding/expected_content_length`.
**Data Shape:** `chunked_encoding: bool | None` — None = "not yet decided"; False = content-length mode; True = chunked mode.

### Decisive source
```python
# :462-477 — single scan decides framing + keep-alive
for name, value in headers:
    ...
    if name == b"content-length" and self.chunked_encoding is None:
        self.expected_content_length = int(value.decode()); self.chunked_encoding = False
    elif name == b"transfer-encoding" and value.lower() == b"chunked":
        self.expected_content_length = 0; self.chunked_encoding = True
    elif name == b"connection" and value.lower() == b"close":
        self.keep_alive = False
...
# :514-517 — nothing declared and body is possible ⇒ declare chunked ourselves
if self.chunked_encoding is None and self.scope["method"] != "HEAD" and status_code not in (204, 304):
    self.chunked_encoding = True
    content.append(b"transfer-encoding: chunked\r\n")
```
```python
# :530-539 — length accounting enforced BOTH directions
if not more_body:
    if self.expected_content_length != 0:
        raise RuntimeError("Response content shorter than Content-Length")
    self.response_complete = True
    ...
    if not self.keep_alive:
        self.transport.close()
```

**Flow:** on first send: default_headers + app headers merged (request's `connection: close` mirrored if absent), then ONE pass over names sets framing mode and may flip keep-alive off. Body writes branch three ways: HEAD zeroes the budget; chunked writes hex-length frames with terminal `0\r\n\r\n`; identity mode decrements the budget and RAISES on overflow ("longer than Content-Length") or underflow at completion ("shorter than"). 1xx-style statuses (204/304) and HEAD suppress the auto-chunk header.
**Invariant:** Framing decision happens exactly once (the `is None` guard) before any body byte; a second `http.response.start` raises. App-supplied `connection: close` MUST win over the request's keep-alive preference — that's the only sanctioned way an app forces teardown.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'status_code not in (204, 304)' uvicorn/uvicorn/protocols/http/httptools_impl.py"` → 1; `bash -c "grep -c 'keep_alive=http_version != \"1.0\"' uvicorn/uvicorn/protocols/http/httptools_impl.py"` → 1 (HTTP/1.0 default-close). Behavioral pins: `tests/protocols/test_http.py` chunked/content-length suites.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"transfer-encoding chunked content-length framing","limit":5,"detail":"ids"}` → resolves the send-path region line-exact.
**Verdict:** Adopt the tri-state framing latch and both length-error directions verbatim. Adapt status set if your HTTP dialect differs. Omit zttp's stricter variant (covered by its own capsule).

