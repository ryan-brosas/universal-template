<!-- capsule-v2 -->
# Cleartext h2c preface sniffing and ALPN dispatch — how does one port negotiate HTTP/1.1 vs HTTP/2 per connection?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** When is the protocol chosen from TLS metadata vs sniffed bytes, and what happens to bytes read before the decision?

## ALPN at connection_made (TLS); PRI-preface prefix-match on cleartext; buffered bytes replayed
**Path/Symbol:** `uvicorn/protocols/http/auto_zttp_impl.py` — preface constant :12, ALPN arm :44–52, idle timer :54, partial-preface hold :68–76, `_switch` :78–89.
**Signature:** `def _switch(self, http2: bool, initial_data: bytes = b"") -> None`; class attrs `alpn_protocols = ["h2", "http/1.1"]`.
**Data Shape:** `HTTP2_PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"` (24-byte magic, RFC 9113 §3.4); `self.buffer` accumulates until decidable.

### Decisive source
```python
# :44-52 — TLS: decide immediately from the negotiated ALPN token
if is_ssl(transport):
    ssl_object = transport.get_extra_info("ssl_object")
    alpn = ssl_object.selected_alpn_protocol() if ssl_object is not None else None
    self._switch(http2=alpn == "h2")
    return
...
# :68-76 — cleartext: hold bytes while they are a PREFIX of the magic
self.buffer += data
if len(self.buffer) < len(HTTP2_PREFACE) and HTTP2_PREFACE.startswith(self.buffer):
    return
...
self._switch(http2=self.buffer.startswith(HTTP2_PREFACE), initial_data=self.buffer)
```
```python
# :78-89 — swap protocol, replay the buffered bytes into the new parser
protocol = protocol_class(config=..., server_state=..., app_state=..., _loop=self.loop)
self.transport.set_protocol(protocol)
protocol.connection_made(self.transport)
if initial_data:
    protocol.data_received(initial_data)
```

**Flow:** connection_made: over TLS pick by `selected_alpn_protocol()=="h2"` with NO byte inspection; on cleartext arm a keep-alive-length timeout that force-closes silent connections, register in shared connections, then per data chunk extend the buffer — if it's still a strict PREFIX of the 24-byte magic, wait for more; otherwise dispatch on full match (`ZttpH2Protocol`) or mismatch (`ZttpProtocol`), passing the WHOLE buffer as initial data so no byte is lost or re-read. The negotiator removes itself from the connections set before switching.
**Invariant:** Prefix-hold is mandatory: a client may split the preface across TCP segments (direct test pins this). The timeout uses `config.timeout_keep_alive` because an abandoned preface-sniff must not leak a connection forever. `_switch` order mirrors the WS relay: set_protocol → connection_made → data_received.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'startswith(HTTP2_PREFACE)' uvicorn/uvicorn/protocols/http/auto_zttp_impl.py"` → 1; behavioral pins `tests/protocols/test_http2.py:test_prior_knowledge_preface_selects_http2` :908, `test_prior_knowledge_preface_split_across_packets` :925, `test_alpn_h2_selects_http2` :896, `test_http1_request_selects_http1` :945.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"prior knowledge cleartext preface sniff negotiator","limit":5,"detail":"ids"}` → rank#1/#2 the two preface tests line-exact.
**Verdict:** Adopt ALPN-first-else-prefix-sniff and the replay-buffer rule verbatim. Adapt for your h2 stack. Omit upgrade-based h2c (RFC-deprecated path) — not implemented here.

