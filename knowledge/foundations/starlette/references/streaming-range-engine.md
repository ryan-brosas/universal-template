<!-- capsule-v2 -->
# StreamingResponse disconnect ladder + FileResponse range engine

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How does streaming stop early when the client hangs up, and what is the full Range/If-Range/multipart-byteranges decision tree?

## StreamingResponse.__call__ — three strategies by ASGI spec version
**Path/Symbol:** `starlette/responses.py:StreamingResponse.__call__` (:257-283) + `listen_for_disconnect` (:242-246).
### Decisive source
```python
spec_version = tuple(map(int, scope.get("asgi", {}).get("spec_version", "2.0").split(".")))
if spec_version >= (2, 4):
    try:
        await self.stream_response(send)
    except OSError:
        raise ClientDisconnect()          # server surfaces disconnect as write failure
else:
    async with create_collapsing_task_group() as task_group:
        async def wrap(func):
            await func()
            task_group.cancel_scope.cancel()
        task_group.start_soon(wrap, partial(self.stream_response, send))
        await wrap(partial(self.listen_for_disconnect, receive))   # first finisher wins
```

**Flow:** spec ≥2.4 servers MUST raise on send-after-disconnect, so a plain try/except suffices; older servers need the two-task race where the disconnect listener cancels the streamer mid-chunk. Sync iterables enter via `iterate_in_threadpool` (each `next()` hopped to a worker thread; StopIteration coerced to `_StopIteration` because raising StopIteration inside async context poisons generators — `concurrency.py:37-59`).
**Probe:** `tests/test_responses.py::test_streaming_response_stops_if_receiving_http_disconnect` (:605), `::test_streaming_response_on_client_disconnects` (:636), sync twin :171.

## FileResponse dispatch tree
**Path/Symbol:** `starlette/responses.py:FileResponse.__call__` (:341-385) with `_handle_simple` (:387-399), `_handle_single_range` (:401), `_handle_multiple_ranges` (:420-454).
**Data Shape:** flags per request: `send_header_only` (HEAD method), `send_pathsend` (`scope.extensions["http.response.pathsend"]` → delegate file IO to the SERVER via one pathsend message). stat_result may be pre-injected (StaticFiles already statted); otherwise `os.stat` in threadpool, FileNotFoundError→RuntimeError, non-regular-file→RuntimeError.

**Flow (the full ladder):**
1. `Range` header absent OR `If-Range` present and NOT matching etag/last-modified → simple 200 (or 304 upstream via StaticFiles' NotModifiedResponse).
2. parse errors: non-bytes unit or inverted ranges → 400 MalformedRangeHeader; any start outside `[0,size)` → 416 with `Content-Range: bytes */{size}`.
3. zero parsed ranges (all parts ignorable) → falls back to simple 200.
4. one range → 206 with rewritten content-range/content-length, seek+read loop capped at end.
5. multiple → 206 `multipart/byteranges; boundary={token_hex(13)}` with PRECOMPUTED content-length from `generate_multipart` (:530-573) — boundary entropy comment pins firefox/chrome at 95-96 bits.
**Invariant:** `_parse_ranges` IGNORES malformed parts (non-numeric, dash-less) rather than failing the whole header, but an empty result AFTER filtering raises "range must be requested"; overlapping ranges are merged sort+fold (:490-497) so Content-Length arithmetic stays exact. max_ranges=100 exceeded → return [] → treated as "must be requested" 400 (deliberate anti-DoS collapse).
**Probe:** `tests/test_responses.py::test_file_response_range_multi` (:757), `::test_file_response_merge_ranges` (:849), `::test_file_response_range_416` (:812), suffix-range :961, count-limit-exceeded :793.

## ETag derivation
**Path/Symbol:** `starlette/responses.py:set_stat_headers` (:331-339).
**Data Shape:** `etag = md5(f"{mtime}-{size}")` quoted; last-modified via `formatdate(mtime, usegmt=True)`; both `setdefault` so StaticFiles/user headers win.
**Probe:** `tests/test_staticfiles.py::test_staticfiles_304_with_etag_match` (:201).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_parse_range_header", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "listen_for_disconnect", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "generate_multipart", limit: 5 });
```

## Verdict
Adopt the spec-version strategy switch and the whole range ladder including the ignore-dont-fail part grammar. Adapt chunk size (64KiB default) and boundary length. Omit pathsend unless your server implements the extension.
