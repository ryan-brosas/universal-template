<!-- capsule-v2 -->
# FlowControl and the 503 admission funnel — how do backpressure and limit_concurrency interact?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** When does a connection stop reading (body high-water), when does the SERVER answer 503 instead of the app, and why is 503 a fake ASGI app rather than a branch?

## Read-side high-water + connections/tasks OR-gate at headers-complete
**Path/Symbol:** `uvicorn/protocols/http/flow_control.py:FlowControl` (:8–34) + `service_unavailable` (:37–47); gate in every HTTP impl's `on_headers_complete`/request handler, e.g. `httptools_impl.py:262–270`.
**Signature:** `def pause_reading/resume_reading/pause_writing/resume_writing(self) -> None`; `async def service_unavailable(scope, receive, send) -> None`.
**Data Shape:** `HIGH_WATER_LIMIT = 65536` bytes inbound body buffer; `FlowControl._is_writable_event: asyncio.Event` starts SET.

### Decisive source
```python
# flow_control.py — idempotent toggles around transport calls
def pause_reading(self) -> None:
    if not self.read_paused:
        self.read_paused = True
        self._transport.pause_reading()
...
# httptools_impl.py :262-270 — app SWAPPED before cycle creation
if self.limit_concurrency is not None and (
    len(self.connections) >= self.limit_concurrency or len(self.tasks) >= self.limit_concurrency
):
    app = service_unavailable
    message = "Exceeded concurrency limit."
    self.logger.warning(message)
else:
    app = self.app
```
```python
# flow_control.py :37-47 — the "app" writes a canned response itself
await send({"type": "http.response.start", "status": 503,
    "headers": [(b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", b"19"), (b"connection", b"close")]})
await send({"type": "http.response.body", "body": b"Service Unavailable", "more_body": False})
```

**Flow:** per-request body chunks accumulate into `cycle.body`; crossing 64 KiB pauses TRANSPORT reads (`flow.pause_reading()`), and `receive()` resumes them before each wait — pull-based backpressure. Admission control runs at headers-complete: if EITHER live-connection count OR in-flight task count ≥ limit, the protocol substitutes the zero-dep `service_unavailable` coroutine as the "app", so the request still flows through the normal run_asgi/send pipeline (access logs, error wrappers, on_response_complete bookkeeping all apply).
**Invariant:** The 503 path must be indistinguishable from a real app to the protocol machinery — that's why it's a callable taking (scope, receive, send), not an inline write. FlowControl toggles are guarded by booleans because asyncio transports are no-ops-but-log when called redundantly... and pause/resume pairs MUST stay balanced or reads stall permanently.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'HIGH_WATER_LIMIT' uvicorn/uvicorn/protocols/http/httptools_impl.py"` → 2 (import+use); behavioral pins `tests/protocols/test_http.py:test_max_concurrency` :768 and `test_oversized_body` family.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"limit concurrency exceeded 503 service unavailable","limit":5,"detail":"ids"}` → resolves `service_unavailable`, `FlowControl`, and `test_max_concurrency` line-exact.
**Verdict:** Adopt both mechanisms verbatim; keep 503-as-app shape. Adapt the limit semantics only if your server lacks shared state. Omit HTTP/2 nuance (see h2 stream capsule for its read-gating variant).

