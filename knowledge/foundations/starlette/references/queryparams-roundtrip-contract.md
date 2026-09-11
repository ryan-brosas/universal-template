<!-- capsule-v2 -->
# QueryParams string round trip — does `str(QueryParams(qs))` preserve the original query?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** What exactly is preserved — and silently coerced — when a raw query string becomes QueryParams and is rendered back?

## QueryParams.__init__/__str__ — parse_qsl(keep_blank_values=True) → urlencode(_list)
**Path/Symbol:** `starlette/datastructures.py:QueryParams` (:378-407); shared idiom in `URL.include_query_params/remove_query_params` (:143-160).
**Signature:** `__init__(self, *args: ImmutableMultiDict | Mapping | list[tuple] | str | bytes, **kwargs) -> None`; `__str__(self) -> str`.
**Data Shape:** str input → `parse_qsl(value, keep_blank_values=True)` (blank params `abc&def` become `("abc","")`/`("def","")`, NOT dropped); bytes input decoded **latin-1** before parse; after super().__init__, every key AND value is `str()`-coerced in both stores. `__str__` = `urlencode(self._list)` over the FULL ordered pair list. Keys are case-SENSITIVE (`"A" not in q`) — unlike Headers.

### Decisive source
```python
if isinstance(value, str):
    super().__init__(parse_qsl(value, keep_blank_values=True), **kwargs)
elif isinstance(value, bytes):
    super().__init__(parse_qsl(value.decode("latin-1"), keep_blank_values=True), **kwargs)
else:
    super().__init__(*args, **kwargs)
self._list = [(str(k), str(v)) for k, v in self._list]
self._dict = {str(k): str(v) for k, v in self._dict.items()}
...
def __str__(self) -> str:
    return urlencode(self._list)
```

**Flow:** `HTTPConnection.query_params` lazily builds `QueryParams(self.scope["query_string"])` (requests.py :139-142). URL builders reuse the same kernel: `params = MultiDict(parse_qsl(self.query, keep_blank_values=True))` → mutate → `urlencode(params.multi_items())` → replace query component.
**Invariant:** `str(QueryParams("a=123&a=456&b=789")) == "a=123&a=456&b=789"` — multiplicity and blank values round-trip losslessly BECAUSE str() renders `_list`, not `_dict`. Rendering from a plain dict would collapse duplicates; parsing with default `parse_qsl` (keep_blank_values=False) would silently delete flag-style params like `?debug`.
**Probe:** `tests/test_datastructures.py::test_url_blank_params` (:331-341: `"abc" in q` with empty-string value); `::test_queryparams` (:344-369: str round trip incl. duplicates); `tests/test_datastructures.py::test_url_query_params` (:72-86: include/remove via URL).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", namePattern: "QueryParams", limit: 8 });
await mcp.codebase_memory.search_graph({ project: "starlette", query: "include_query_params remove_query_params urlencode", limit: 10 });
```

## Verdict
Adopt keep_blank_values parsing + full-list rendering as one contract; they only work together. Adapt latin-1 to your server's mandated encoding for raw bytes. Omit type-preserving storage — this class deliberately flattens everything to str at construction. Coverage clean ×2 paths; probes executed green at pin.
