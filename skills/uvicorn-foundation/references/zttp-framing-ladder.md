<!-- capsule-v2 -->
# zttp framing conflict ladder — which response headers are dropped or rewritten when the parser is strict?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** When an app emits Content-Length AND Transfer-Encoding, or TE on a 204, what does the server send on the wire?

## TE dropped on <200/204; CL dropped when both present; auto-chunk when neither
**Path/Symbol:** `uvicorn/protocols/http/zttp_impl.py:RequestResponseCycle.send` — TE strip :434–440, scan :442–452, CL-on-conflict drop :453–458, auto-chunk :460–463, completion close via should_close :517–521.
**Signature:** first-phase of `async def send(self, message)` (response.start arm), before `conn.send_response`.
**Data Shape:** local flags `has_content_length/has_transfer_encoding:bool`, `bodyless = HEAD or status in (204,304) or status<200`.

### Decisive source
```python
# :434-440 — RFC 9112 §6.1: no Transfer-Encoding on 1xx/204 (HEAD/304 keep it)
if status < 200 or status == 204:
    headers = [(n, v) for n, v in headers if n.lower() != b"transfer-encoding"]
...
# :453-463 — conflict resolution + mandatory framing
if has_transfer_encoding and has_content_length:
    headers = [(n, v) for n, v in headers if n.lower() != b"content-length"]
    has_content_length = False
    self.expected_content_length = 0
if not bodyless and not has_transfer_encoding and not has_content_length:
    self.chunked_encoding = True
    headers = headers + [(b"transfer-encoding", b"chunked")]
```
```python
# :517-521 — close decision covers request-close AND response-close directions
# `should_close()` covers both: the request's Connection:close / HTTP/1.0 default,
# and a `close` the response we just wrote declared.
if not self.keep_alive or self.conn.should_close():
    self.transport.close()
```

**Flow:** app headers merged over defaults → conditional TE strip for statuses where chunking is illegal → single scan records framing intents → if the strict backend would reject dual framing, Content-Length silently loses (TE wins) → if NOTHING frames the body and one is possible, uvicorn adds `transfer-encoding: chunked` itself because ztplib refuses to serialize an unframed body. Body phase then honors bodyless suppression and length accounting like the httptools path.
**Invariant:** The wire NEVER carries both CL and TE, never carries TE on 1xx/204, and never sends an unframed body. Contrast with h11_impl/httptools_impl which raise RuntimeErrors on length mismatch — here conflicts are RESOLVED by dropping headers instead, because the backend raises LocalProtocolError that would otherwise kill the connection.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'status < 200 or status == 204' uvicorn/uvicorn/protocols/http/zttp_impl.py"` → 1; `bash -c "grep -c 'has_transfer_encoding and has_content_length' uvicorn/uvicorn/protocols/http/zttp_impl.py"` → 1; `bash -c "grep -c 'conn.should_close()' uvicorn/uvicorn/protocols/http/zttp_impl.py"` → 1.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"zttp transfer encoding content length conflict chunked","limit":5,"detail":"ids"}` → resolves the send-path region line-exact.
**Verdict:** Adopt the precedence ladder (strip-illegal → drop-CL-on-conflict → auto-chunk) verbatim for strict-parser ports. Adapt status sets. Omit HTTP/1.0 default-close nuance (kept_alive handled by should_close).

