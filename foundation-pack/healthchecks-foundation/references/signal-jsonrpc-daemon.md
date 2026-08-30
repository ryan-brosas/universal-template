<!-- capsule-v2 -->
# Signal-cli JSON-RPC transport — newline-delimited replies, CAPTCHA recovery, and permanent-error taxonomy

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do you drive a long-lived messaging daemon over a socket from a synchronous web worker — correlating replies, bounding total latency, and recovering from rate-limit CAPTCHAs?

## hc/integrations/signal/transport.py: Signal.send / _read_replies / notify
**Path/Symbol:** `signal/transport.py:Signal.Result/Response/Data/Error/Reply` pydantic models (:37-58), `send` (:63-101), `_read_replies` (:103-148), `notify` (:150-176); style pipeline `hc/lib/html.py:extract_signal_styles` (:42-77).
**Signature:** `send(cls, recipient: str, message: str) -> None`; `_read_replies(cls, payload_bytes: bytes) -> Iterator[bytes]`; `TIMEOUT = 60` class constant; notify retry ladder `tries_left = 2`.
**Data Shape:** jsonrpc "2.0" send payload with uuid4 id; Reply model tolerates id="" and error.data=None; result.type ∈ {UNREGISTERED_FAILURE, RATE_LIMIT_FAILURE,...}; styles are "idx:len:TAG" strings (BOLD/MONOSPACE).

### Decisive source
```python
# signal/transport.py — total-time budget across a byte-at-a-time read loop
start = time.time()
...
with socket.socket(stype, socket.SOCK_STREAM) as s:
    s.settimeout(cls.TIMEOUT)
    s.connect(address); s.sendall(payload_bytes)
    s.shutdown(socket.SHUT_WR)          # we are done sending
    buffer = []
    while True:
        ch = s.recv(1)
        buffer.append(ch)
        if ch in (b"\n", b""):
            yield b"".join(buffer)
            buffer = []
        if time.time() - start > cls.TIMEOUT:
            raise TransportError("signal-cli call timed out")

# ...and the recovery ladder in notify():
except SignalRateLimitFailure as e:
    self.channel.send_signal_captcha_alert(e.token, e.reply.decode())   # ops: submit via submitchallenge
    plaintext, _ = extract_signal_styles(text)
    self.channel.send_signal_rate_limited_notice(text, plaintext)       # user: what happened
    raise
except TransportError as e:
    tries_left -= 1
    if e.permanent or tries_left == 0:
        raise
```

**Flow:** notify → TokenBucket.authorize_signal (6/min per hashed phone) → render template → extract Signal text-styles from limited HTML subset (b/code only, no nesting, entities unescaped; mismatched tags assert-fail) → send(): username recipients get "u:" prefix; replies are matched by uuid id, UNREGISTERED_FAILURE raises TransportError(permanent=True), RATE_LIMIT_FAILURE carries the captcha token out as SignalRateLimitFailure. Non-permanent failures retry exactly once.
**Invariant:** The wall-clock check INSIDE the recv loop exists because per-op settimeout resets on every successful read — without it a chatty daemon streams forever. shutdown(SHUT_WR) is how you tell signal-cli the request ended without closing the read side. User-facing error strings never embed raw daemon replies (log them, show a code) but CAPTCHA replies are deliberately relayed to the OPERATOR channel because they contain the one-time token needed to unblock. The dual-notification CAPTCHA path makes an error a first-class workflow trigger, not just a failure.
**Probe:** `hc/integrations/signal/tests/test_notify.py::test_it_handles_special_characters`, `test_it_obeys_rate_limit` (bucket drained → error), `test_it_requires_signal_cli_socket`, `hc/lib/tests/test_html.py::ExtractSignalTestCase::test_it_rejects_mismatched_tags` (AssertionError), `test_it_unescapes_html`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "signal send replies captcha timeout", limit: 10 });
```

## Verdict
Adopt id-correlated newline framing with a wall-clock ceiling, permanent-vs-transient classification shared with HttpTransport semantics, single-retry ladders, and operator-vs-user split on rate-limit failures. Adapt to your daemon protocol; keep "log the raw reply, never ship it to the user". Omit style extraction if plain text suffices — but keep the mismatched-tag hard fail rather than silent mangling.
