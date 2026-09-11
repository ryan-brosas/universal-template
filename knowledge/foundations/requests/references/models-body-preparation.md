<!-- capsule-v2 -->
# Body preparation ladder — how do json/data/files/streamed bodies decide Content-Length vs Transfer-Encoding?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** In `prepare_body`, what is the decision tree from (data, files, json) to body bytes + framing headers?

## PreparedRequest.prepare_body (+_encode_params/_encode_files)
**Path/Symbol:** `src/requests/models.py:PreparedRequest.prepare_body` (:576-652), `.prepare_content_length` (:654-668), `RequestEncodingMixin._encode_params` (:150-180), `._encode_files` (:182-251).
**Signature:** `prepare_body(data, files, json=None) -> None`.

### Decisive source
```python
if not data and json is not None:
    content_type = "application/json"
    try:
        body = complexjson.dumps(json, allow_nan=False)   # NaN/Inf REJECTED
    except ValueError as ve:
        raise InvalidJSONError(ve, request=self)
    if not isinstance(body, bytes):
        body = body.encode("utf-8")
is_iterable = isinstance(data, Iterable) or hasattr(data, "__iter__")
if is_iterable and not isinstance(data, (str, bytes, list, tuple, Mapping)):
    # streamed body: generator / file-like
    length = super_len(data) or None      # TypeError/AttributeError/UnsupportedOperation → None
    body = data
    if getattr(body, "tell", None) is not None:
        try:
            self._body_position = body.tell()     # record for redirect rewind
        except OSError:
            self._body_position = object()        # sentinel: rewind will raise UnrewindableBodyError
    if files:
        raise NotImplementedError("Streamed bodies and files are mutually exclusive.")
    if length:
        self.headers["Content-Length"] = builtin_str(length)
    else:
        self.headers["Transfer-Encoding"] = "chunked"
else:
    ...multipart via _encode_files OR urlencoded via _encode_params...
    self.prepare_content_length(body)
```
and `prepare_content_length`: body present → CL=super_len if nonzero; body falsy AND method not GET/HEAD AND no CL → `Content-Length: 0`.

### Decisive source (rewind contract)
```python
# sessions.py resolve_redirects:
rewindable = prepared_request._body_position is not None and (
    "Content-Length" in headers or "Transfer-Encoding" in headers)
if rewindable:
    rewind_body(prepared_request)
# utils.rewind_body: seek(_body_position) else UnrewindableBodyError;
# object() sentinel makes rewindable True so callers GET UnrewindableBodyError
# instead of hanging the connection.
```

**Flow:** json-only path (allow_nan=False → InvalidJSONError) → streamed-iterable path (tell() position recorded, OSError→object() sentinel, files XOR streams, CL-or-chunked) → raw-data path (files→multipart with 2/3/4-tuples incl. custom headers; else dict/list→urlencoded utf-8, str/bytes/file-like pass through with no content-type override unless form-encoded) → CL fallback rules.
**Invariant:** The `object()` sentinel is deliberate tri-state: None = not-streamed (no rewind attempted), int = rewind target, object() = rewind SHOULD be attempted and must fail LOUDLY (UnrewindableBodyError) rather than hang. Multipart rejects string data (`ValueError("Data must not be a string.")`) and skips `None` file entries defensively. GET/HEAD never get implicit `Content-Length: 0`.
**Probe:** Direct tests: `tests/test_requests.py::test_json_param_post_content_type_works` (:2161) pins body-stage output; `::test_chunked_upload_does_not_set_content_length_header` (:2275); super_len edge matrix `tests/test_utils.py::TestSuperLen` ×7 (:50-152). `grep -n "_body_position = object()" src/requests/models.py` → 1 hit (:620).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "prepare_body", limit: 10 });
```

## Verdict
Adopt the three-path tree, allow_nan=False, and the tri-state `_body_position` contract. Adapt JSON encoder flags to host policy. Omit py2 basestring branches.
