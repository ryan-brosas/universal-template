<!-- capsule-v2 -->
# Lazy 100-Continue — why is "Expect: 100-continue" answered only when the app reads the body?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** Where does the interim response get written, and what suppresses it after the first receive?

## Flag set at header parse; written inside receive(); cleared on first fire
**Path/Symbol:** set in `httptools_impl.py:on_header` :216–219; consumed in `RequestResponseCycle.receive` :553–557; state carried on cycle `waiting_for_100_continue` (:236, :466).
**Signature:** `async def receive(self) -> ASGIReceiveEvent` — first branch before the event wait.
**Data Shape:** parser callback flag `self.expect_100_continue:bool` → per-cycle `waiting_for_100_continue:bool`.

### Decisive source
```python
# httptools_impl.py :553-557
async def receive(self) -> ASGIReceiveEvent:
    if self.waiting_for_100_continue and not self.transport.is_closing():
        self.transport.write(b"HTTP/1.1 100 Continue\r\n\r\n")
        self.waiting_for_100_continue = False
```
```python
# h11 variant asks the PARSER who is waiting (:403, :516-521)
self.waiting_for_100_continue = conn.they_are_waiting_for_100_continue
...
if self.waiting_for_100_continue and not self.transport.is_closing():
    event = h11.InformationalResponse(status_code=100, headers=[], reason="Continue")
    output = self.conn.send(event=event)
```

**Flow:** client sends `Expect: 100-continue` → protocol records the intent at header time (h11: queried from connection state when the cycle starts) → app calls `receive()` for the body → FIRST call writes the interim `100 Continue` (raw bytes in httptools; FSM-serialized in h11) and clears the latch → subsequent receives skip. An app that never reads the body never gets the interim response, so the client times out holding its bytes instead of wasting the upload.
**Invariant:** The write must happen ONLY on the transport being open and exactly once (`waiting_for_...` latch cleared synchronously). Sending 100 unprompted or twice desyncs naive clients; sending it before the app opts in defeats the whole mechanism.
**Probe:** from the uvicorn checkout root: behavioral pins `tests/protocols/test_http.py:test_100_continue_sent_when_body_consumed` :809 and `test_100_continue_not_sent_when_body_not_consumed` :840 — the pair pins BOTH directions of the lazy behavior.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"expect 100 continue waiting body consumed","limit":5,"detail":"ids"}` → resolves both direct tests line-exact.
**Verdict:** Adopt receive()-triggered interim response verbatim. Adapt serialization form to your HTTP writer. Omit zttp's `event.expect_continue` plumbing nuance (same semantics).

