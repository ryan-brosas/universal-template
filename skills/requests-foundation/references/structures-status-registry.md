<!-- capsule-v2 -->
# Status-code registry — how does `requests.codes` expose aliases as both attributes and items, and what happens on a miss?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `requests`. **Question:** How do I build the same bidirectional-feeling status-name registry without inheriting its silent lookup traps?

## codes._init over LookupDict
**Path/Symbol:** `src/requests/status_codes.py:_init` (:109-125), `codes` (:106); `src/requests/structures.py:LookupDict` (:96-130).
**Signature:** `_init() -> None`; `LookupDict(name=None)`, `__getitem__(key) -> _VT | None`, `.get(key, default=None)`.
**Data Shape:** `_codes: dict[int, tuple[str, ...]]` (several aliases per code, incl. non-identifier jokes like `"\\o/"`, `"✓"` for 200); `codes = LookupDict(name="status_codes")`.

### Decisive source
```python
codes: LookupDict[int] = LookupDict(name="status_codes")

def _init():
    for code, titles in _codes.items():
        for title in titles:
            setattr(codes, title, code)              # alias lands in INSTANCE __dict__
            if not title.startswith(("\\", "/")):
                setattr(codes, title.upper(), code)  # guarded uppercase twin

# LookupDict:
def __getattr__(self, key):
    if key in self.__dict__:
        return self.__dict__[key]
    raise AttributeError(...)            # unknown ATTR is loud
def __getitem__(self, key):              # unknown ITEM is silent
    return self.__dict__.get(key, None)
```

**Flow:** import → `_init()` walks every `(code, aliases)` pair → each alias becomes an instance attribute equal to the code, plus an upper-cased twin unless the alias starts with `\` or `/` (regex/punctuation names would form absurd attributes) → attribute access resolves via `__getattr__`, item access via `__getitem__`.
**Invariant:** The dict storage itself stays **empty forever** — all state lives in instance `__dict__`. Therefore `len(codes) == 0` and `'ok' in codes` are NOT registry queries; only `codes.get(...)` / attribute access are. Miss semantics split: `.get`/`[]` return None silently, `codes.ok_missing` raises AttributeError.
**Probe:** Direct test: `tests/test_requests.py::test_status_code_425` (:2913-2926) pins all six case variants (`TOO_EARLY/too_early/UNORDERED/unordered/UNORDERED_COLLECTION/unordered_collection`) to `425` through `.get`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "requests", query: "LookupDict status codes init", limit: 10 });
```

## Verdict
Adopt the alias-table→setattr build and the loud-attr/silent-item miss split. Adapt the uppercase-twin rule if your host forbids non-ASCII attributes (`✓`). Omit the docstring self-extension (`global __doc__`) unless your docs tooling consumes it.
