<!-- capsule-v2 -->
# lstr origin-trace propagation — how does provenance survive arbitrary string mutations?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** When model output text is interpolated, sliced, joined or transformed before the next LLM call, how do I keep knowing which invocation(s) produced it?

## `_lstr` trace algebra
**Path/Symbol:** `src/ell/types/_lstr.py:_lstr` (:85-107 `__new__`, :186-194 `__add__`, :196-226 `__mod__`, :228-258 mul, :260-277 `__getitem__`, :279-318 `__getattribute__` wrapper, :321-463 join/split/partition family).
**Signature:** `_lstr(content: str, logits: Optional[np.ndarray] = None, origin_trace: Optional[Union[str, FrozenSet[str]]] = None)`.
**Data Shape:** subclass of `str`; metadata lives in instance attribute `__origin_trace__: FrozenSet[str]`; a bare string origin is normalized to a singleton frozenset at construction; empty `_lstr()` has `frozenset()`.

### Decisive source
```python
# __add__, _lstr.py:185-194
new_content = super(_lstr, self).__add__(other)
self_origin = self.__origin_trace__

if isinstance(other, _lstr):
    new_origin = self_origin
    new_origin = new_origin.union(other.__origin_trace__)
else:
    new_origin = self_origin

return _lstr(new_content, None, frozenset(new_origin))
```

```python
# __getattribute__ generic wrapper, _lstr.py:300-318
if callable(attr) and name not in _lstr.__dict__:
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        result = attr(*args, **kwargs)
        if isinstance(result, str):
            origin_traces = self.__origin_trace__
            for arg in args:
                if isinstance(arg, _lstr):
                    origin_traces = origin_traces.union(arg.__origin_trace__)
            for key, value in kwargs.items():
                if isinstance(value, _lstr):
                    origin_traces = origin_traces.union(value.__origin_trace__)
                return _lstr(result, None, origin_traces)
        return result
    return wrapped
return attr
```

**Flow:** every producing operation (`+`, `%`, `*`, index/slice, any inherited str method not overridden here) computes content via `super()`, unions the operand traces, and returns a fresh `_lstr` with `logits=None`. Indexing is special-cased (:276): slicing always nulls logits — "you are divorcing the logits of the indexed result from their context" (in-source comment) — but keeps origin traces. Split/partition helpers union the *separator's* trace into all parts.
**Invariant:** mutation never loses origins (union-only growth), and never fabricates them (plain-str operands contribute nothing). A porter that resets traces on transform breaks the studio dependency graph; one that keeps per-character provenance is over-engineering — granularity IS the whole invocation id set.
**Probe:** `tests/test_lstr.py` (`test_add` pins union semantics: `(s1 + s2).origin_trace == frozenset({"model2"})`; `test_join` pins separator+parts union; `test_getitem` pins slice preservation; `test_upper` pins the generic-method wrapper path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "_lstr __origin_trace__ lstr", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.types._lstr._lstr.origin_trace @ src/ell/types/_lstr.py:154-161
```

## Verdict
Adopt the frozenset-union algebra and the str-subclass trick verbatim — it is pure Python. Adapt the operation list to your language's string API surface (every mutating method needs coverage or provenance silently dies there). Omit the vestigial `logits` parameter plumbing unless you have token-level scores to carry; upstream already nulls it everywhere.
