<!-- capsule-v2 -->
# super_len body measurement — how is the remaining length of any stream/file/bytes object derived without consuming it?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What probe ladder computes Content-Length for arbitrary bodies, and which exceptions mean "unknown length"?

## utils.super_len
**Path/Symbol:** `src/requests/utils.py:super_len` (:160-228).
**Signature:** `super_len(o: Any) -> int` (never negative).
**Data Shape:** Accepts str/bytes, objects with `__len__`, `.len`, `fileno()`, `tell()`/`seek()`; returns remaining-bytes count.

### Decisive source
```python
if not is_urllib3_1 and isinstance(o, str):
    o = o.encode("utf-8")        # urllib3 2.x treats str as utf-8, not latin-1
if hasattr(o, "__len__"):
    total_length = len(o)
elif hasattr(o, "len"):          # urllib3 request objects expose .len
    total_length = o.len
elif hasattr(o, "fileno"):
    try: fileno = o.fileno()
    except (io.UnsupportedOperation, AttributeError):   # TarFile.extractfile, issue #5229
        pass
    else:
        total_length = os.fstat(fileno).st_size
        if "b" not in o.mode:
            warnings.warn(... FileModeWarning ...)     # text-mode length may be wrong
if hasattr(o, "tell"):
    try: current_position = o.tell()
    except OSError:                                     # stdin-like special fds
        if total_length is not None: current_position = total_length
    else:
        if hasattr(o, "seek") and total_length is None: # StringIO: seek-end probe
            try:
                o.seek(0, 2); total_length = o.tell()
                o.seek(current_position or 0)           # restore for partial reads
            except OSError:
                total_length = 0
return max(0, total_length - current_position)
```

**Flow:** len attr ladder (dunder → .len → fstat size, with text-mode warning) → current-position probe (tell, OSError-tolerant) → StringIO-style seek-to-end discovery WITH position restore → remaining = max(0, total − current).
**Invariant:** The function measures REMAINING bytes (partially-read files report what's left — pinned by `test_super_len_correctly_calculates_len_of_partially_read_file`). tell-OSError with known total treats position as at-END (so remaining=0) rather than lying about 0 consumed. The seek probe MUST restore the original position (`o.seek(current_position or 0)`) — omitting that consumes the caller's stream. utf-8 encoding of str exists solely because urllib3 2.x changed str semantics.
**Probe:** Direct tests: `tests/test_utils.py::TestSuperLen` — partially-read file :66, weird tell errors :73/:86 parametrized, `__len__` :127, no-`__len__` :132, tell :139, fileno :145, no-matches :151. `grep -n "o.seek(0, 2)" src/requests/utils.py` → 1 hit (:216).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "super_len", limit: 10 });
```

## Verdict
Adopt the full probe ladder including position restore and the two OSError adjudications. Adapt warnings to host logging. Omit the urllib3-1.x str branch when pinning urllib3 2.x only.
