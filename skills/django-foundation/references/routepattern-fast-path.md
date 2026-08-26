<!-- capsule-v2 -->
# RoutePattern fast path — when does path() matching avoid regex entirely, and what does a converter ValueError mean?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** How does `<int:pk>`-style routing compile and match, and why does a converter rejecting its input NOT produce a 500?

## Route grammar with converter backtracking
**Path/Symbol:** `django/urls/resolvers.py` — `_route_to_regex` (249–290), `RoutePattern.match` (324–346), `RoutePattern.__init__` (317–322).
**Signature:** `_route_to_regex(route, is_endpoint) -> tuple[str, dict[str, Converter]]`; `match(self, path) -> tuple[str, (), dict] | None`.
**Data Shape:** `<converter:name>` compiles to `(?P<name>{converter.regex})`; endpoint routes anchor with `\Z`; whitespace inside angle brackets raises ImproperlyConfigured; parameter names must be valid Python identifiers.

### Decisive source
```python
def match(self, path):
    # Only use regex overhead if there are converters.
    if self.converters:
        if match := self.regex.search(path):
            kwargs = match.groupdict()
            for key, value in kwargs.items():
                converter = self.converters[key]
                try:
                    kwargs[key] = converter.to_python(value)
                except ValueError:
                    return None          # converter rejected: try NEXT pattern
            return path[match.end() :], (), kwargs
    elif self._is_endpoint:
        if self._route == path:
            return "", (), {}
    elif path.startswith(route := str(self._route)):
        return path.removeprefix(route), (), {}
    return None
```

**Flow:** converters present → regex search → run each captured value through `to_python`; ANY ValueError aborts this pattern (returns None so the resolver's loop tries the next route) → no converters + endpoint ⇒ plain string equality → no converters + prefix ⇒ startswith + removeprefix.
**Invariant:** (1) A converter is a two-way contract (`to_python` for resolve, `to_url` for reverse) whose rejection is ROUTE-LEVEL failure, not request failure — that is how `/articles/foo/` can fall through from an int route to a catch-all. (2) The string-equality fast path only applies to converter-free endpoints; adding one converter flips the whole match onto the regex branch. (3) `_route_to_regex` is `@functools.lru_cache`d — compiled patterns are shared across threads and must stay immutable.
**Probe:** `tests/urlpatterns/tests.py::ConverterTests` (:260) + `tests/urlpatterns/test_resolvers.py` — direct tests pinning converter registration, `to_python` failures falling through, and path() parameter validation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "_route_to_regex RoutePattern to_python converters", limit: 10 });
```

## Verdict
Adopt converter-as-contract with fall-through-on-rejection for any declarative routing DSL; adapt the grammar tokens; keep the lru_cache immutability assumption or drop the cache. Direct converter suites cited executed green at this pin.
