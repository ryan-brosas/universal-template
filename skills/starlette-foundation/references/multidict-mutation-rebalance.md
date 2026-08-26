<!-- capsule-v2 -->
# MultiDict mutation rebalance — how do writes keep `_dict` and `_list` coherent?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** When code mutates a multi-dict (`md["a"] = x`, `setlist`, `update`, `poplist`), which positions survive and which value wins?

## MultiDict — every mutator rewrites both structures
**Path/Symbol:** `starlette/datastructures.py:MultiDict` (:322-375) — `__setitem__` :323-324, `__delitem__` :326-328, `pop/popitem/poplist` :330-342, `setdefault` :348-353, `setlist` :355-361, `append` :363-365, `update` :367-375.
**Signature:** `setlist(self, key: Any, values: list[Any]) -> None`; `update(self, *args, **kwargs) -> None`.
**Data Shape:** mutable subclass of ImmutableMultiDict. Mutators never mutate a pair in place (except append); they rebuild `_list` by key-filtered comprehension and then re-point/patch `_dict`.

### Decisive source
```python
def setlist(self, key: Any, values: list[Any]) -> None:
    if not values:
        self.pop(key, None)
    else:
        existing_items = [(k, v) for (k, v) in self._list if k != key]
        self._list = existing_items + [(key, value) for value in values]
        self._dict[key] = values[-1]

def update(self, *args, **kwargs) -> None:
    value = MultiDict(*args, **kwargs)
    existing_items = [(k, v) for (k, v) in self._list if k not in value.keys()]
    self._list = existing_items + value.multi_items()
    self._dict.update(value)
```

**Flow:** `md["a"] = v` ≡ `setlist("a", [v])`: all old `a` rows are filtered out, the new pair is appended AT THE END (key moves to end of iteration), and `_dict[a]` becomes the new last value. `setlist("b", [])` is exactly `pop("b")`. `update()` removes every incoming key first, then appends the whole incoming multiplicity — so `q.update(q)` is identity-safe. `poplist(key)` collects values from `_list` BEFORE delegating to `pop`, returning the full multiplicity.
**Invariant:** after ANY mutation, `_dict` must equal `{k: last-v-for-k}` over `_list`. A porter who only patches `_dict` leaves stale rows in `multi_items()` (breaks urlencode round trips); one who only rewrites `_list` breaks `[]` reads.
**Probe:** `tests/test_datastructures.py::test_multidict` (:488-549): setitem collapses to single value; del removes all rows; pop returns last ("456"); poplist returns ["123","456"]; setlist moves + replaces; empty-setlist removes; update({"a":"789"}) keeps b's position; self-update identity.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", namePattern: "MultiDict", limit: 8 });
await mcp.codebase_memory.search_graph({ project: "starlette", query: "setlist update poplist mutation", limit: 10 });
```

## Verdict
Adopt the filter-rebuild discipline and the "empty list == remove" rule verbatim; adopt "new rows go to the end" because URL.include_query_params output ordering depends on it. Adapt naming to your host's collection API. Omit in-place row patching — it does not exist here for keyed writes. Tests executed green at pin.
