<!-- capsule-v2 -->
# HTTP pipelining deque — how are requests that arrive while another response is in flight ordered and started?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** Where do parsed-but-not-started pipelined requests WAIT, and what re-arms the keep-alive timer vs. the queue?

## deque of (cycle, app) + appendleft/pop FIFO discipline
**Path/Symbol:** `uvicorn/protocols/http/httptools_impl.py` — `self.pipeline: deque` init :113; decision :291–298; drain in `on_response_complete` :332–347.
**Signature:** `if existing_cycle is None or existing_cycle.response_complete: _start_asgi_task(...) else: self.flow.pause_reading(); self.pipeline.appendleft((self.cycle, app))`.
**Data Shape:** `deque[tuple[RequestResponseCycle, ASGI3Application]]`; per-request scope built at `on_message_begin`, cycle at headers-complete.

### Decisive source
```python
# :291-298
existing_cycle = self.cycle
...
if existing_cycle is None or existing_cycle.response_complete:
    self._start_asgi_task(self.cycle, app)     # start immediately
else:
    self.flow.pause_reading()                  # stop parsing further bytes
    self.pipeline.appendleft((self.cycle, app))
...
# :342-347 — previous response just completed
if self.pipeline:
    cycle, app = self.pipeline.pop()
    self._start_asgi_task(cycle, app)
else:
    self.timeout_keep_alive_task = self.loop.call_later(
        self.timeout_keep_alive, self.timeout_keep_alive_handler)
```

**Flow:** request #2's headers complete while #1 is mid-response ⇒ its (cycle, app) goes into the deque and transport reads PAUSE (no point buffering unbounded pipelines) ⇒ when #1 finishes (`on_response_complete`: counter++, resume reads) the NEXT cycle pops from the RIGHT (appendleft+pop = FIFO) and starts its ASGI task ⇒ only when the pipeline is EMPTY does the 5s keep-alive timer arm instead.
**Invariant:** Exactly one active cycle per connection; ordering is strictly arrival order. The keep-alive timeout and the pipeline are mutually exclusive branches — a queued request must never be killed by an idle-timeout. `lenient_data_after_close=True` (:66) lets the parser swallow bytes after a close so a client that pipelines behind `Connection: close` doesn't poison the 400 path.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'pipeline.appendleft' uvicorn/uvicorn/protocols/http/httptools_impl.py"` → 1; `bash -c "grep -c 'lenient_data_after_close=True' uvicorn/uvicorn/protocols/http/httptools_impl.py"` → 1; behavioral pins `tests/protocols/test_http.py:test_pipelined_requests` :506 + `test_keepalive_timeout_with_pipelined_requests` :431.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"pipelined requests deque queue cycle","limit":5,"detail":"ids"}` → rank#1 `test_pipelined_requests` :506-524 line-exact.
**Verdict:** Adopt deque-FIFO + pause-reads-while-queued verbatim for any HTTP/1.x server. Adapt: h11 achieves ordering differently (PAUSED state machine, see h11-twin capsule). Omit benchmark variants.

