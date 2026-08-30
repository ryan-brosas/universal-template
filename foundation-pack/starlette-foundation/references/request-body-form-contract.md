<!-- capsule-v2 -->
# Request.stream/body/form — single-consumption contract and the form() contextmanager duality

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** What happens when body(), stream(), json(), and form() are called in different orders on the same Request?

## Request.stream
**Path/Symbol:** `starlette/requests.py:Request.stream` (:234-252).
**Signature:** `async def stream(self) -> AsyncGenerator[bytes, None]`.
**Data Shape:** flags `_stream_consumed`, `_is_disconnected`, optional cached `_body`.

### Decisive source
```python
if hasattr(self, "_body"):
    yield self._body; yield b""; return        # body()-first: replay once, then EOF sentinel
if self._stream_consumed:
    raise RuntimeError("Stream consumed")      # stream()-twice: hard error
while not self._stream_consumed:
    message = await self._receive()
    if message["type"] == "http.request":
        ...
        if not message.get("more_body", False):
            self._stream_consumed = True
    elif message["type"] == "http.disconnect":
        self._is_disconnected = True
        raise ClientDisconnect()
yield b""                                      # ALWAYS terminates with empty chunk
```

**Flow:** `body()` (:254-260) just joins `stream()` chunks into `_body`; `json()` caches parsed `_json`. The trailing `yield b""` is load-bearing — parsers that iterate until empty chunk terminate without needing generator semantics.
**Invariant:** exactly ONE of {cached-body replay, live consumption} per request; second stream() raises instead of silently returning nothing. Disconnect raises ClientDisconnect rather than ending quietly so callers can distinguish abort from empty POST.
**Probe:** `tests/test_requests.py` (31 tests incl. body-then-stream orderings); `tests/middleware/test_base.py::test_read_request_stream_in_app_after_middleware_calls_body` (:631).

## _get_form content-type gate + HTTP 400 promotion
**Path/Symbol:** `starlette/requests.py:_get_form` (:268-311).
**Data Shape:** `parse_options_header(Content-Type)` → route to `MultiPartParser` (`b"multipart/form-data"`), `FormParser` (`b"application/x-www-form-urlencoded"`), or EMPTY FormData (anything else — no error!). Limits default `max_files=1000, max_fields=1000, max_part_size=1MiB`.
### Decisive source
```python
except MultiPartException as exc:
    if "app" in scope:                    # inside a Starlette app
        raise HTTPException(status_code=400, detail=exc.message)   # → handler renders it
    raise exc                             # standalone: raw parser error
```
**Invariant:** unknown Content-Type yields an empty form, NOT a 415 — form parsing is opt-in by header, matching HTML form behavior.
**Probe:** `tests/test_formparsers.py::test_no_request_data` (:438); limit tests :475/:689/:716.

## form() as AwaitableOrContextManager
**Path/Symbol:** `starlette/requests.py:form` (:313-322) + `starlette/_utils.py:AwaitableOrContextManagerWrapper` (:64-79).
**Data Shape:** returns a wrapper that is BOTH awaitable (→ FormData) and an async CM whose `__aexit__` awaits `.close()` — closing every UploadFile spool. `await request.form()` leaks tempfiles unless GC saves you; `async with request.form() as form:` guarantees cleanup.
**Probe:** `tests/test_formparsers.py::test_multipart_request_files` (:157) uses plain await; UploadFile.close contract via FormData.close (:494-497 datastructures).

## Misc kernels
- `cookie_parser` (:46-70): Django-derived lenient split(";")/split("=")/strip + `http.cookies._unquote`; no-value chunks become `{"": chunk}` entries keyed by EMPTY string; multi Cookie headers merge left-to-right via getlist loop (:150-159). Probe: `tests/test_requests.py` cookie tests.
- `send_push_promise` (:342-348): gated on `scope["extensions"]["http.response.push"]`; copies ONLY `SERVER_PUSH_HEADERS_TO_COPY` (accept*, cache-control, user-agent).
- `is_disconnected` (:328-340): CANCELLED CancelScope trick — pre-cancels the scope so `receive()` returns immediately if no message is buffered.
- `HTTPConnection.base_url` (:116-130): builds from `app_root_path` (NOT current root_path) with query stripped; `url_for` resolves name through `scope.get("router") or scope.get("app")` then makes absolute (:198-203). Probe: `tests/test_routing.py::test_url_for_with_root_path` (:540).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "stream", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_get_form", limit: 5 });
```

## Verdict
Adopt the one-consumption contract byte-for-byte (it's what FastAPI's dependency caching sits on). Adopt the 400-promotion gate keyed on `"app" in scope`. Adapt limits upward for your workload but keep them EXISTING — unbounded multipart is a DoS. Omit push-promise when targeting HTTP/2-pure servers that reject the extension anyway.
