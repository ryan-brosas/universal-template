<!-- capsule-v2 -->
# URL tri-form constructor — how do I build a URL object from a string, a scope, or loose components without the forms fighting each other?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** What are the three mutually exclusive URL construction forms, and why does `__str__` return the original string instead of re-rendering parsed components?

## Constructor + lazy SplitResult cache
**Path/Symbol:** `starlette/datastructures.py:URL.__init__` (:29-67), `URL.components` (:69-73), `URL.__str__` (:165-166).
**Signature:** `def __init__(self, url: str = "", scope: Scope | None = None, **components: Any) -> None`.
**Data Shape:** exactly ONE of {`url` string, `scope`, `**components`}; asserts reject pairwise combinations (`'Cannot set both "url" and "scope".'` etc.). Stores only `self._url: str`; all accessors derive from a memoized `SplitResult`.

### Decisive source
```python
elif components:
    assert not url, 'Cannot set both "url" and "**components".'
    url = URL("").replace(**components).components.geturl()   # components form DELEGATES to replace()
...
self._url = url

@property
def components(self) -> SplitResult:
    if not hasattr(self, "_components"):
        self._components = urlsplit(self._url)   # parse once, on first property touch
    return self._components

def __str__(self) -> str:
    return self._url                              # VERBATIM original bytes, never re-rendered
```

**Flow:** scope form → Host-header trust gate (see url-scope-reconstruction; `_HOST_RE`) → server-tuple fallback with default-port elision (http:80/https:443/ws:80/wss:443) → netloc=None renders authority-less `f"{path}?{query}"` (:56-62). Components form recursively round-trips through `replace()`. First accessor call parses once into `_components`; every later accessor (scheme/netloc/path/query/fragment/username/password/hostname/port) reads the cached tuple.
**Invariant:** `str(url)` is byte-identical to the string it was built from — parsing is a view, not a normalization pass, so scope-derived paths survive `urlsplit/geturl` quirks untouched. Equality is string equality (`__eq__ :162-163`: `str(self) == str(other)`), so a URL equals its plain-string form.
**Probe:** `tests/test_datastructures.py::test_url_from_scope` (:124-170 — empty-query elision, server default-port 443 dropped, host header kept verbatim); `::test_url` (:19-29 — component reads incl. fragment).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", namePattern: "^URL$", limit: 5 });
await mcp.codebase_memory.get_code_snippet({ project: "starlette", qualified_name: "starlette.starlette.datastructures.URL.__init__" });
```

## Verdict
Adopt the tri-form constructor with pairwise asserts and store-the-string/lazy-parse shape — it makes URLs cheap to construct per-request and impossible to half-specify. Adapt the default-port table to your schemes. Omit nothing in the assert lattice: silently accepting `URL("http://x", scheme="https")` produces order-dependent URLs. Coverage caveat: the `**components` direct form has no dedicated test at this pin (it is exercised only via include/replace_query_params paths).
