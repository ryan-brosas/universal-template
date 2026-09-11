<!-- capsule-v2 -->
# Body single-consumption + size gates — how does request.body interact with POST parsing, and where do DATA_UPLOAD limits fire?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** Why can't you read `body` after touching `POST` on multipart requests, and what is the exact early-rejection ladder for oversized uploads?

## Stream-state machine with two-stage size gate
**Path/Symbol:** `django/http/request.py:HttpRequest.body` (399–434), `_check_data_too_big` (436–442), `_load_post_and_files` (448–492), `read`/`readline` (507–519).
**Signature:** `body` property → bytes; `read(self, *args, **kwargs)`; guards via `RawPostDataException`, `RequestDataTooBig`, `UnreadablePostError`.
**Data Shape:** `_read_started` latch set by ANY stream read; after `.body` the raw stream is replaced with `BytesIO(_body)`; limit = `settings.DATA_UPLOAD_MAX_MEMORY_SIZE` checked against BOTH declared Content-Length AND actual seekable stream size.

### Decisive source
```python
@property
def body(self):
    if not hasattr(self, "_body"):
        if self._read_started:
            raise RawPostDataException(
                "You cannot access body after reading from request's data stream")
        try:
            content_length = int(self.META.get("CONTENT_LENGTH") or 0)
        except (ValueError, TypeError):
            content_length = 0          # ASGIRequest comma-joins duplicates
        self._check_data_too_big(content_length)      # stage 1: declared size
        if self._stream.seekable():
            stream_size = self._stream.seek(0, os.SEEK_END)
            self._check_data_too_big(stream_size)     # stage 2: ACTUAL size
            self._stream.seek(0)
        try:
            self._body = self.read()
        except OSError as e:
            raise UnreadablePostError(*e.args) from e
        finally:
            self._stream.close()
        self._stream = BytesIO(self._body)
    return self._body
```
and `_load_post_and_files`: multipart errors call `_mark_post_parse_error()` then RE-RAISE; urlencoded bodies MUST be UTF-8 (`BadRequest` otherwise per RFC 1866).

**Flow:** any read sets `_read_started` → `.body` refuses if the stream was already consumed without caching → gate on declared Content-Length → gate on real buffered size (chunked transfer can understate Content-Length) → slurp, close original, swap in BytesIO.
**Invariant:** (1) Single-consumption is enforced by exception, not by returning empty bytes — silent empties hide double-read bugs. (2) The seekable-stream second gate exists because `Transfer-Encoding: chunked` bodies have absent/understated CONTENT_LENGTH; a porter checking only the header keeps an OOM hole. (3) Failed POST parses poison `_post/_files` so error-page rendering that re-touches POST doesn't re-trigger the original failure.
**Probe:** `tests/asgi/tests.py::MaxMemorySizeASGITests` (:850, incl. `test_body_size_exceeded_without_content_length` pinning the actual-size stage) + `test_request_too_big_request_error` (:229); multipart parse-error poisoning pinned by `tests/handlers/tests.py::HandlerTests.test_invalid_multipart_boundary` (:85).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "HttpRequest body _check_data_too_big _read_started", limit: 10 });
```

## Verdict
Adopt the latch + two-stage size gate for any buffered-body reader; adapt setting names and exception classes; omit the utf-8-only urlencoded rule only if you accept legacy non-UTF-8 form posts knowingly. Direct suites cited executed green at this pin.
