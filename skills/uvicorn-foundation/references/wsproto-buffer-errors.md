<!-- capsule-v2 -->
# wsproto message buffer and error-hint close — how is ws_max_size enforced across fragments, and what closes on protocol errors?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** Why is text counted as UTF-8 BYTES, and what does uvicorn write when the REMOTE breaks the protocol?

## WebsocketBuffer byte-budget; FrameTooLargeError → 1009 with reason; err.event_hint reply
**Path/Symbol:** `uvicorn/protocols/websockets/wsproto_impl.py` — buffer class :38–68 (byte count :53), size enforcement in handle_message :250–268, remote-error arm :164–172 (`err.event_hint`), post-close data arm :169–173, peer-close echo :278–287.
**Signature:** `def extend(self, event: events.TextMessage | events.BytesMessage) -> None` / `def to_message(self) -> WebSocketReceiveEvent`.
**Data Shape:** `WebsocketBuffer{value: BytesIO|StringIO|None, length:int, max_length:int}`; type picked by FIRST fragment.

### Decisive source
```python
# :52-55 — ws_max_size is a BYTE budget: encode() text before counting
self.length += len(event.data.encode()) if isinstance(event, events.TextMessage) else len(event.data)
if self.length > self.max_length:
    raise FrameTooLargeError
...
# :258-266 — overflow ⇒ close 1009 with human-readable reason
except FrameTooLargeError:
    self.close_sent = True
    reason = f"Message exceeds the maximum size ({self.config.ws_max_size} bytes)"
    self.queue.put_nowait({"type": "websocket.disconnect", "code": 1009, "reason": reason})
    ...
```
```python
# :164-173 — malformed input: wsproto hands back the exact error frame to send
except RemoteProtocolError as err:
    self.transport.write(self.conn.send(err.event_hint))
    self.transport.close()
except LocalProtocolError:
    # e.g. a pong racing our close — just drop the transport
    self.transport.close()
```

**Flow:** each Text/Bytes fragment extends the running buffer (StringIO vs BytesIO chosen once by the first fragment's type); crossing ws_max_size raises → uvicorn queues disconnect 1009 + sends CloseConnection(1009, reason) + closes. Complete messages queue as websocket.receive then pause reads until consumed. RemoteProtocolError (bad frames/handshake) writes wsproto's OWN prebuilt error bytes (`err.event_hint`) so status/reason match the violation exactly.
**Invariant:** Counting str chars instead of encoded bytes would let multi-byte UTF-8 exceed the declared limit by up to 4× — the `.encode()` is load-bearing. After close_sent, only CloseConnection events are processed (:219–223 guard); everything else is ignored until the peer echoes.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'len(event.data.encode())' uvicorn/uvicorn/protocols/websockets/wsproto_impl.py"` → 1; `bash -c "grep -c 'FrameTooLargeError' uvicorn/uvicorn/protocols/websockets/wsproto_impl.py"` → 3; behavioral pins `test_fragmented_message_exceeding_max_size` :762, `test_fragmented_message_reassembly` :785, `test_send_binary_data_to_server_bigger_than_default_on_websockets` :712.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"websocket buffer max size fragmented reassembly","limit":5,"detail":"ids"}` → resolves WebsocketBuffer + direct tests line-exact.
**Verdict:** Adopt byte-budget counting and event_hint echo verbatim. Adapt buffer container. Omit permessage-deflate negotiation details (library-level).

