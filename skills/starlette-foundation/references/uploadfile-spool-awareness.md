<!-- capsule-v2 -->
# UploadFile spool awareness — write/read/close route around the event loop based on roll state

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** When must file IO hop to a thread and when is it safe inline, and how does the wrapper know?

## UploadFile roll prediction
**Path/Symbol:** `starlette/datastructures.py:UploadFile` (:410-479).
**Data Shape:** wraps a BinaryIO (in practice SpooledTemporaryFile); captures `_max_mem_size = getattr(file, "_max_size", 0)` at construction; `_in_memory` checks `file._rolled` (default True for foreign handles → conservative threadpool); `_will_roll(size_to_add)` predicts `tell() + size > max_mem_size`.
### Decisive source
```python
async def write(self, data: bytes) -> None:
    if self.size is not None: self.size += len(data)
    if self._will_roll(len(data)):
        await run_in_threadpool(self.file.write, data)   # about-to-disk or already-disk
    else:
        self.file.write(data)                            # small + in-memory → inline, no hop
```
**Flow:** read/seek/close mirror the same `_in_memory` gate. size accounting happens BEFORE the branch so callers can trust `upload.size` even after failed writes.
**Invariant:** the private-attribute probes (`_max_size`, `_rolled`) are SpooledTemporaryFile internals — documented here as load-bearing; porting to another spool type means re-deriving both.
**Probe:** `tests/test_formparsers.py::test_multipart_request_large_file_rollover_in_background_thread` (:349) pins the real-threadpool rollover.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_will_roll", limit: 5 });
```

## Verdict
Adopt the predict-then-hop pattern for any spooled sink; it removes ~all threadpool overhead for small uploads without risking event-loop blocking on large ones. Adapt thresholds if your spool differs. Omit nothing — this is already minimal.
