<!-- capsule-v2 -->
# Response header initialization + cookie emission — content-length/content-type population rules

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** When does a Response auto-set Content-Length/Content-Type, and how do multiple Set-Cookie headers coexist with a Mapping-based header bag?

## Response.init_headers
**Path/Symbol:** `starlette/responses.py:Response.init_headers` (:55-81) + `render` (:48-53).
**Data Shape:** user headers lowercased latin-1 pairs; `populate_content_length` skipped if user supplied one OR status `<200 or in {204,304}`; `populate_content_type` only when media_type set AND user didn't override.

### Decisive source
```python
if (body is not None and populate_content_length
        and not (self.status_code < 200 or self.status_code in (204, 304))):
    raw_headers.append((b"content-length", str(len(body)).encode("latin-1")))
if content_type is not None and populate_content_type:
    if content_type.startswith("text/") and "charset=" not in content_type.lower():
        content_type += "; charset=" + self.charset      # utf-8 class default
```

**Flow:** `render()` maps None→b"", bytes|memoryview→as-is, else `.encode(charset)`; JSONResponse overrides render with `json.dumps(..., ensure_ascii=False, allow_nan=False, separators=(",", ":"))` — compact, NaN-illegal (:194-201).
**Invariant:** 304/204 must never carry content-length (RFC 9110 §8.6); a porter who unconditionally appends it breaks caching revalidation. Header VALUES are latin-1 encoded — non-latin1 chars raise at construction, not at send time.
**Probe:** `tests/test_responses.py` (response-header param block :14-100 incl. 204/304 length checks); `::test_streaming_response_unknown_size` (:574) shows StreamingResponse bypassing init_headers' length logic entirely.

## set_cookie / delete_cookie
**Path/Symbol:** `starlette/responses.py:set_cookie` (:89-132), `delete_cookie` (:134-152).
**Data Shape:** builds an `http.cookies.SimpleCookie`, serializes via `cookie.output(header="").strip()`, then APPENDS `(b"set-cookie", val)` to raw_headers — N cookies = N header entries (never merged). `samesite` asserted ∈ {strict,lax,none} with default "lax"; `partitioned` raises on Python <3.14. delete_cookie = set_cookie(max_age=0, expires=0, same path/domain/samesite...).
**Invariant:** because deletion goes through the SAME append path with the SAME attributes, a cookie set with `path="/x"` can only be deleted with matching path — the default `/` silently fails otherwise.
**Probe:** `tests/test_responses.py` set-cookie tests (:101-153 region: max_age/expires/samesite assertions).

## WebSocket denial + background hook
**Path/Symbol:** `starlette/responses.py:_wrap_websocket_denial_send` (:154-161), used by `Response.__call__` (:163-170), `StreamingResponse.__call__` (:257-263), `FileResponse.__call__` (:341-346).
**Flow:** on websocket scopes the send shim renames `http.response.*` → `websocket.http.response.*` so the same response objects serve HTTP-rejection of WS handshakes; background task runs AFTER body for plain responses.
**Probe:** `tests/test_websockets.py::test_send_denial_response` (:310), `::test_send_denial_response_with_file_response` (:346).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "init_headers", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "set_cookie", limit: 5 });
```

## Verdict
Adopt the population-suppression matrix verbatim. Adopt multi-entry Set-Cookie appending (dict-style merging is the classic porting bug). Adapt charset injection policy per your media types.
