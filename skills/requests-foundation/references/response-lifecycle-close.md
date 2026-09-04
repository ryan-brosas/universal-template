<!-- capsule-v2 -->
# Response lifecycle — who may close a Response, what does close do to an unconsumed stream, and what does pickling force?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `requests`. **Question:** How do I release a streamed response's connection safely without consuming its body, and what happens when a Response is pickled mid-stream?

## Response.__enter__/__exit__ / close / __getstate__/__setstate__
**Path/Symbol:** `src/requests/models.py:Response.__enter__` (:812-813), `.__exit__` (:815-816), `.close` (:1173-1184), `.__getstate__` (:818-824), `.__setstate__` (:826-832).
**Signature:** `close() -> None`; `__getstate__() -> dict[str, Any]` over `self.__attrs__`.
**Data Shape:** depends on `raw` (urllib3 response with optional `release_conn`) and `_content_consumed` flag; no return values.

### Decisive source
```python
def __exit__(self, *args):
    self.close()                       # with-block ALWAYS closes

def close(self) -> None:
    if not self._content_consumed:
        self.raw.close()               # only the UNCONSUMED path closes raw
    release_conn = getattr(self.raw, "release_conn", None)
    if release_conn is not None:
        release_conn()                 # pool return attempted on EVERY path

def __getstate__(self):
    if not self._content_consumed:
        self.content                   # pickling FORCES full consumption
    return {attr: getattr(self, attr, None) for attr in self.__attrs__}

def __setstate__(self, state):
    ...                                # restored responses have raw=None
    setattr(self, "_content_consumed", True)
```

**Flow:** context-manager exit or explicit close → if body never read, close the raw stream; then unconditionally call `release_conn()` when present so the connection returns to the urllib3 pool → pickling intercepts unconsumed responses and reads `.content` first (memoizing the tri-state `_content`), while unpickling fabricates a raw-less, already-consumed response.
**Invariant:** close is safe on BOTH consumed and unconsumed responses but is NOT a no-op twice on fake/raw-less responses unless guarded — porters must keep the `getattr(raw, "release_conn", None)` tolerance because build_response can attach plain file-like raws. After unpickling, `.raw` is None forever: any retry/re-send path must use `r.connection`, not `r.raw`. An unconsumed streamed response that is closed stays `_content_consumed=False` yet its connection IS released — later `.content` access raises RuntimeError("already consumed").
**Probe:** Direct tests: `tests/test_requests.py::test_response_context_manager` (:2185-2189, `response.raw.closed` after with-block), `::test_unconsumed_session_response_closes_connection` (:2191-2198, asserts BOTH `_content_consumed is False` AND `raw.closed`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "requests", query: "Response close release_conn getstate", limit: 10 });
```

## Verdict
Adopt the two-step close (conditional raw.close + unconditional release_conn) and consume-on-pickle. Adapt `release_conn` naming to the host pool API keeping the getattr-guard. Omit `__nonzero__`-era py2 shims.
