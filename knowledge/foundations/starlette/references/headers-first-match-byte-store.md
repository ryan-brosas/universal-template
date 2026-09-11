<!-- capsule-v2 -->
# Headers byte-store — why does `headers["x"]` return the FIRST match while `params["x"]` returns the last?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** How does an immutable header view stay lossless over duplicate, mixed-case headers while looking like a plain Mapping?

## Headers — raw latin-1 row list, first-match reads
**Path/Symbol:** `starlette/datastructures.py:Headers` (:500-574) — constructors :505-522, `raw` :524-526, `getlist` :537-539, `__getitem__` :544-549, `mutablecopy` :541-542, `items` :534-535.
**Signature:** `Headers(headers: Mapping | None = None, raw: list[tuple[bytes, bytes]] | None = None, scope: MutableMapping | None = None)`.
**Data Shape:** single `_list: list[tuple[bytes, bytes]]`; keys lowercased and latin-1 encoded on ingress; every decode is latin-1. The three constructors are mutually exclusive under asserts; the scope form ALIASES a normalized list back into the scope: `self._list = scope["headers"] = list(scope["headers"])` (normalizes server tuples AND makes later mutations of that list visible to this view). Unlike ImmutableMultiDict there is NO `_dict`: reads are linear scans.

### Decisive source
```python
elif scope is not None:
    # scope["headers"] isn't necessarily a list
    # it might be a tuple or other iterable
    self._list = scope["headers"] = list(scope["headers"])
...
def __getitem__(self, key: str) -> str:
    get_header_key = key.lower().encode("latin-1")
    for header_key, header_value in self._list:
        if header_key == get_header_key:
            return header_value.decode("latin-1")
    raise KeyError(key)
```

**Flow:** `HTTPConnection.headers` builds once lazily with `Headers(scope=self.scope)` (requests.py :133-136). First-match lookup wins for `[]`/`.get` — the OPPOSITE winner rule vs multi-dict last-wins — while `getlist()` returns all values in wire order (this is how multiple Cookie headers are merged by requests.py :150-159). `len()` counts RAW ROWS including duplicates; `keys()/values()/items()` deliberately override Mapping defaults to mirror rows 1:1 without dedupe; `mutablecopy()` shallow-copies rows preserving duplicates for downstream MutableHeaders edits.
**Invariant:** never normalize to a dict at construction: duplicate headers (Cookie, Set-Cookie on parse paths, Vary) are legal and ordered; case-insensitivity must be enforced per-comparison against the stored lowercase bytes, not by rewriting the wire casing seen in `raw`.
**Probe:** `tests/test_datastructures.py::test_headers` (:226-250); `::test_headers_mutablecopy` (:313-318 — duplicates preserved then collapsed by setitem at FIRST position); `::test_mutable_headers_from_scope` (:321-328 — tuple scope normalized through aliasing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", namePattern: "Headers", limit: 8 });
await mcp.codebase_memory.search_graph({ project: "starlette", query: "latin-1 lower encode decode header", limit: 10 });
```

## Verdict
Adopt: byte-row store, per-comparison case folding, first-match single reads + ordered getlist, non-deduping views, scope-aliasing constructor. Adapt latin-1 only if your ASGI layer mandates otherwise (it does not — the spec fixes latin-1). Omit a dict cache: correctness here depends on scans staying order-faithful. All cited tests executed green at pin.
