<!-- capsule-v2 -->
# Content consumption — what are iter_content's error remaps, the _content tri-state, and iter_lines' pending-line rule?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** How do Response.iter_content/iter_lines/content/text/json translate urllib3 stream errors and manage consumed state?

## Response.iter_content / content / text / json / iter_lines
**Path/Symbol:** `src/requests/models.py:Response.iter_content` (:914-977), `.iter_lines` (:994-1032), `.content` (:1035-1051), `.text` (:1054-1089), `.json` (:1091-1124), `.close` (:1173-1184).
**Signature:** `iter_content(chunk_size=1, decode_unicode=False) -> Iterator`; `content -> bytes | None` property.

### Decisive source
```python
def generate():
    if hasattr(self.raw, "stream"):
        try:
            yield from self.raw.stream(chunk_size, decode_content=True)
        except ProtocolError as e:
            raise ChunkedEncodingError(e)
        except DecodeError as e:
            raise ContentDecodingError(e)
        except ReadTimeoutError as e:
            raise ConnectionError(e)
        except SSLError as e:
            raise RequestsSSLError(e)
    ...
    self._content_consumed = True

if self._content_consumed and isinstance(self._content, bool):
    raise StreamConsumedError()      # False sentinel = never had content
...
# content property:
if self._content is False:           # False = unconsumed sentinel
    if self._content_consumed:
        raise RuntimeError("The content for this response was already consumed")
    if self.status_code == 0 or self.raw is None:
        self._content = None         # transport-level failure → None content
    else:
        self._content = b"".join(self.iter_content(CONTENT_CHUNK_SIZE)) or b""
```
and the iter_lines boundary rule:
```python
if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
    pending = lines.pop()     # last segment may continue in next chunk — hold it back
else:
    pending = None
yield from lines
...
if pending is not None:
    yield pending             # flush at true end of stream
```

**Flow:** urllib3 path remaps four exception types mid-stream (mid-iteration failures surface as requests exceptions) → file-like fallback loops raw.read → consumed flag set only AFTER generator exhausts → `.content` joins 10KiB chunks once, memoizes, status_code==0/raw-None → None → `.text` decodes header charset else apparent_encoding (chardet) else utf-8, always errors="replace", LookupError/TypeError fallbacks → `.json` tries BOM-detected utf-8/16/32 decode first then falls back to `.text` parse, both wrapped into requests.JSONDecodeError preserving msg/doc/pos.
**Invariant:** `_content=False` (sentinel) vs `_content=None` (transport failure) vs bytes is tri-state; StreamConsumedError fires only when iterating an ALREADY-consumed stream response. iter_lines' tail-comparison heuristic holds back a possibly-incomplete final line across chunk boundaries — dropping it corrupts every streamed-line consumer; keeping it requires flushing `pending` post-loop exactly as written.
**Probe:** Direct tests: `tests/test_requests.py::test_iter_content_wraps_exceptions` (:1536, parametrized over the exact four remap pairs), `::test_prepare_body_position_non_stream` (:2007), `::test_stream_timeout` (:2537); `grep -n "_content_consumed and isinstance(self._content, bool)" src/requests/models.py` → 1 hit (:958).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "iter_content StreamConsumed ProtocolError", limit: 10 });
```

## Verdict
Adopt error remap table, tri-state content, and pending-line rule byte-for-byte. Adapt chunk sizes freely. Omit apparent_encoding's chardet-vs-charset_normalizer detection choice to host policy (keep utf-8 floor).
