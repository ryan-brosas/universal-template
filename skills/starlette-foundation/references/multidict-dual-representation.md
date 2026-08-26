<!-- capsule-v2 -->
# ImmutableMultiDict dual representation — what does `d[key]` return when a key repeats?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** When a query string or form contains a key twice, which value does mapping-style access return, and how do equality and views behave?

## ImmutableMultiDict — `_dict` last-wins + `_list` ordered-all
**Path/Symbol:** `starlette/datastructures.py:ImmutableMultiDict.__init__` (:256-282), `:getlist` (:284-285), `:__getitem__` (:299-300), `:__eq__` (:311-314).
**Signature:** `__init__(self, *args: ImmutableMultiDict | Mapping | Iterable[tuple[K,V]], **kwargs) -> None`.
**Data Shape:** two parallel stores built once from `_items`: `self._dict = {k: v for k, v in _items}` (dict-comprehension ⇒ LAST occurrence wins) and `self._list = _items` (every pair, arrival order). All Mapping views (`keys/values/items/__iter__/__len__/__contains__`) delegate to `_dict`, so they DEDUPE; `getlist()` filters `_list`; `multi_items()` returns a defensive copy of `_list`.

### Decisive source
```python
self._dict = {k: v for k, v in _items}
self._list = _items
...
def getlist(self, key: Any) -> list[_CovariantValueType]:
    return [item_value for item_key, item_value in self._list if item_key == key]
...
def __eq__(self, other: Any) -> bool:
    if not isinstance(other, self.__class__):
        return False
    return sorted(self._list) == sorted(other._list)
```

**Flow:** construct from pairs/Mapping/another multi-dict → dict comprehension silently keeps the last duplicate → per-key reads split into two APIs: `q["a"]`/`.get("a")` = last value; `q.getlist("a")` = all values in order.
**Invariant:** `__eq__` is exact-class (`isinstance(other, self.__class__)`) AND order-insensitive but multiplicity-sensitive (`sorted(_list)`). `QueryParams(...) != FormData(...)` even with identical items; `!= "invalid"` for plain mappings/strings. Never "fix" this to compare `_dict`s — it would erase multiplicity.
**Probe:** `tests/test_datastructures.py::test_queryparams` (:344-369: `q["a"] == "456"`, `getlist("a") == ["123","456"]`, cross-constructor `==`, `!= "invalid"`); `::test_multidict` (:463-486); `::test_formdata` (:426-446).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", query: "multi_items getlist repeated key", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "starlette", namePattern: "ImmutableMultiDict", limit: 5 });
```

## Verdict
Adopt the two-store shape verbatim: one dedup map + one full ordered list, with the read API split (`[]`=last, `getlist`=all). Adapt key/value coercion to your host's types. Omit nothing in `__eq__`: class-exactness prevents QueryParams==FormData accidents, sorted-list comparison keeps multiplicity meaningful. Direct tests executed green at pin (38 passed); all cited paths coverage-clean.
