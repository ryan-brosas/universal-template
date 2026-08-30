<!-- capsule-v2 -->
# MultiPartParser callback state machine — spooled files, deferred writes, error-close ledger

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How do you drive python-multipart's sync callbacks from an async request stream without blocking the loop or leaking tempfiles?

## MultiPartParser.parse — write/finish queues drained per chunk
**Path/Symbol:** `starlette/formparsers.py:MultiPartParser.parse` (:247-297) + callbacks `on_part_begin` (:178), `on_part_data` (:181-188), `on_part_end` (:190-203), `on_headers_finished` (:219-242).
**Data Shape:** callbacks are SYNC (called inside `parser.write(chunk)`); file data cannot be written there (UploadFile.write is async/threadpool) so two queues bridge: `_file_parts_to_write: list[(MultipartPart, bytes)]`, `_file_parts_to_finish: list[MultipartPart]`.

### Decisive source
```python
async for chunk in self.stream:
    parser.write(chunk)
    for part, data in self._file_parts_to_write:
        await part.file.write(data)      # threadpool hop via UploadFile.write
    for part in self._file_parts_to_finish:
        await part.file.seek(0)          # rewind finished uploads
    self._file_parts_to_write.clear()
    self._file_parts_to_finish.clear()
parser.finalize()
```

**Flow:** `on_headers_finished` decides field-vs-file by presence of a `filename` option; files get a `SpooledTemporaryFile(max_size=1MiB)` registered in `_files_to_close_on_error` BEFORE any data flows; `on_part_data` enforces max_part_size ONLY for non-file parts (file parts stream to disk, bounded by the spool). UploadFile is appended to items at part END even though bytes may still arrive — safe because parse() finishes all writes before returning.
**Invariant:** on ANY BaseException mid-parse, every spooled tempfile in the error-ledger is closed then the exception re-raised (:291-295) — no orphan fd. A porter who closes only successfully-parsed files leaks one fd per aborted upload.
**Probe:** `tests/test_formparsers.py::test_too_many_files_raise` (:716), `::test_multipart_request_large_file_rollover_in_background_thread` (:349).

## Charset + decode fallback
**Path/Symbol:** `starlette/formparsers.py:parse` charset block (:248-253) + `_user_safe_decode` (:45-49).
**Data Shape:** boundary comes from Content-Type params (KeyError → MultiPartException "Missing boundary"); optional `charset` param decoded latin-1; `_user_safe_decode` falls back to latin-1 on UnicodeDecodeError OR LookupError (unknown codec name supplied by client).
**Probe:** `tests/test_formparsers.py::test_missing_boundary_parameter` (:633), `::test_user_safe_decode_ignores_wrong_charset` (:621).

## FormParser (urlencoded) — same message discipline
**Path/Symbol:** `starlette/formparsers.py:FormParser.parse` (:105-143) + size counters (:75-99).
**Data Shape:** QuerystringParser callbacks append `(FormMessage, bytes)` tuples to `self.messages`; the async loop DRAINS the list after each chunk (`list(self.messages); clear()`) and reassembles name/value bytearrays; on FIELD_END both are `unquote_plus`d from latin-1 bytes. Counters: `_current_field_size` per field vs max_part_size; `_current_fields` incremented at END vs max_fields — so an oversized field aborts mid-field and an over-quota field aborts at completion.
**Probe:** `tests/test_formparsers.py::test_urlencoded_limits_stop_parsing_within_a_single_chunk` (:593) pins that limits fire INSIDE one large chunk.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "parse", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_user_safe_decode", limit: 5 });
```

## Verdict
Adopt the queue-drain-per-chunk pattern whenever your parser lib has sync callbacks but your file sinks are async; adopt the close-on-error ledger unconditionally. Adapt spool threshold to your RAM budget. Omit FormParser if your framework delegates urlencoded bodies elsewhere — it's ~40 lines of glue over python-multipart either way.
