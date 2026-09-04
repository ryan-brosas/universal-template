<!-- capsule-v2 -->
# MutableHeaders live-list kernel — why do response.header edits reach the wire but FileResponse copies first?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** When middleware does `response.headers["x"] = "y"` after construction, what guarantees the edit is in the ASGI start message — and where must you copy instead?

## MutableHeaders — replace-in-place writes + LIVE `raw`
**Path/Symbol:** `starlette/datastructures.py:MutableHeaders.__setitem__` (:578-598), `append` :649-655, `raw` override :627-629, `setdefault` :631-643, `add_vary_header` :657-661, `__or__/__ior__` :614-625. Consumers: `starlette/responses.py:Response.headers` (:84-86), start message (:166), `set_cookie` (:132), FileResponse copies (:404, :432).
**Signature:** `MutableHeaders(raw: list[tuple[bytes, bytes]] | None = None, ...)`; `raw` property returns the LIVE `_list`.
**Data Shape:** `__setitem__` collects all indexes of the key, deletes duplicates `[1:]` in reverse, then REPLACES index `[0]` in place — value updates keep position; new keys append. `append` never dedupes (Set-Cookie multiplicity). The overridden `raw` property hands out `_list` itself (immutable `Headers.raw` returns a copy at :524-526).

### Decisive source
```python
for idx in reversed(found_indexes[1:]):
    del self._list[idx]
if found_indexes:
    idx = found_indexes[0]
    self._list[idx] = (set_key, set_value)
else:
    self._list.append((set_key, set_value))
...
@property
def raw(self) -> list[tuple[bytes, bytes]]:
    return self._list          # LIVE — no copy
```

**Flow:** Response.init_headers stores a plain list on `self.raw_headers`; the `headers` property wraps that SAME list in MutableHeaders (`MutableHeaders(raw=self.raw_headers)`); `send({"type": "http.response.start", ..., "headers": self.raw_headers})` emits that same object — so post-construction edits by CORS/gzip/session middleware are visible on the wire with zero re-plumbing. FileResponse instead builds `MutableHeaders(raw=list(self.raw_headers))` when computing conditional headers (ETag/Range decisions) so probe-time mutations can't corrupt the emitted rows.
**Invariant:** two aliases of one list (view + wire payload) is the contract; breaking it means middleware headers silently vanish. The reverse discipline matters too: read-modify-write paths that must not leak (conditional-request computation) copy explicitly. `|`/`|=` accept any Mapping else raise TypeError.
**Probe:** `tests/test_datastructures.py::test_mutable_headers` (:253-266 — setdefault no-overwrite, del removes all, raw equality); `::test_headers_mutablecopy` (:313-318 — duplicate collapse keeps FIRST position); `::test_mutable_headers_merge*` (:269-310); consumer pinned by tests/middleware/test_cors.py + test_gzip.py suites (green at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", query: "MutableHeaders raw response start", limit: 10 });
await mcp.codebase_memory.trace_path({ project: "starlette", function_name: "starlette.starlette.datastructures.MutableHeaders", direction: "inbound", limit: 20 });
```

## Verdict
Adopt the shared-list aliasing between mutable header views and the emitted ASGI message, plus explicit copies for decision-only mutation. Adapt `|`-merge sugar freely. Omit defensive copying inside `raw` — the whole point is wire visibility; copying belongs at call sites like FileResponse. Coverage clean ×2 paths; datastructures suite 38/38 green at pin.
