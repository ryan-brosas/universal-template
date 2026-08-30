<!-- capsule-v2 -->
# GZipResponder identity/gzip split — header deferral, streaming flush, thread-offload threshold

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How does compression middleware decide AFTER seeing response headers, and what does it do with streaming bodies and uncompressible content?

## IdentityResponder.send_with_compression — defer-until-known
**Path/Symbol:** `starlette/middleware/gzip.py:IdentityResponder.send_with_compression` (:105-169).
**Data Shape:** `http.response.start` is HELD in `self.initial_message` (never sent immediately); classification flags: `content_encoding_set` (already compressed → passthrough), `partial_response` (status 206 → never recompress ranges), `content_type_is_excluded` (media type or `type/*` hits DEFAULT_EXCLUDED_CONTENT_TYPES incl. event-stream/images/fonts/zips).

### Decisive source
```python
elif message_type == "http.response.body" and not self.started:
    self.started = True
    body = message.get("body", b""); more_body = message.get("more_body", False)
    if len(body) < self.minimum_size and not more_body:   # small single-shot → skip
        await self.send(self.initial_message); await self.send(message)
    elif not more_body:                                    # standard: compress + fix length
        body = await self.apply_compression(body, more_body=False)
        headers["Content-Length"] = str(len(body))         # only if body CHANGED
    else:                                                  # streaming start: drop length
        ...
        del headers["Content-Length"]                      # length now unknown
```

**Flow:** gzip chosen at REQUEST time (`"gzip" in Accept-Encoding`), but whether to compress is decided at RESPONSE-start time; streaming uses zlib `Z_SYNC_FLUSH` per chunk so the client sees progressive data; pathsend messages bypass entirely.
**Invariant:** Content-Encoding/Length are rewritten ONLY when compressed bytes differ from raw — a porter who always sets them emits invalid framing on incompressible payloads. Vary: Accept-Encoding added on every compression decision.
**Probe:** `tests/middleware/test_gzip.py::test_gzip_streaming_response_emits_output_per_chunk` (:278), `::test_gzip_ignored_on_range_responses` (:258), `::test_gzip_ignored_for_small_responses` (:55).

## apply_compression thread ladder
**Path/Symbol:** `starlette/middleware/gzip.py:GZipResponder.apply_compression` (:204-214) + `_get_gzip_capacity_limiter` (:32-41).
**Data Shape:** chunks ≥ `thread_minimum_size` (128KiB) compress via `anyio.to_thread.run_sync(..., limiter=dedicated CapacityLimiter(40))`; smaller inline. Limiter lives in a `RunVar` so it's per-event-loop, isolated from anyio's default 40-thread pool.
**Invariant:** compressor object is created LAZILY via property (allocation only once real compression starts) with `16 + MAX_WBITS` → gzip wrapper (not raw deflate).
**Probe:** `::test_gzip_compression_in_thread` (:98), `::test_gzip_streaming_compression_in_thread` (:118).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "apply_compression", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_get_gzip_capacity_limiter", limit: 5 });
```

## Verdict
Adopt the subclass split (IdentityResponder base / GZipResponder override) — it cleanly separates "should this transport transform?" from "how?". Adapt thresholds and exclusion list. Omit the dedicated limiter only if your framework already bounds worker threads.
