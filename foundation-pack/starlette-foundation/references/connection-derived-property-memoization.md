<!-- capsule-v2 -->
# Connection derived-property memoization — when does a request's parsed view stop tracking the live scope?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** If middleware mutates `scope["headers"]` or `query_string` after an endpoint has read `request.headers` once, what does the endpoint see?

## hasattr-guarded compute-once ladder
**Path/Symbol:** `starlette/requests.py:HTTPConnection.url/base_url/headers/query_params/cookies/state` (:110-196).
**Signature:** uniform pattern: `@property def x(self): if not hasattr(self, "_x"): self._x = derive_from_scope(); return self._x`.
**Data Shape:** private cache slot per property (`_url`, `_base_url`, `_headers`, `_query_params`, `_cookies`, `_state`) stored on instance `__dict__`.

### Decisive source
```python
@property
def query_params(self) -> QueryParams:
    if not hasattr(self, "_query_params"):  # pragma: no branch
        self._query_params = QueryParams(self.scope["query_string"])
    return self._query_params

@property
def state(self) -> StateT:
    if not hasattr(self, "_state"):
        self.scope.setdefault("state", {})      # the ONE exception: aliases live dict
        self._state = State(self.scope["state"])
    return cast(StateT, self._state)
```

**Flow:** first access derives from the scope and memoizes; every later access returns the SAME object. Consequence ladder: url/query_params/headers/cookies are SNAPSHOTS — scope mutations after first access are invisible to them; `state` deliberately breaks the pattern by wrapping the scope's own dict (see state-scope-write-through). Parsing cost (URL split, cookie parse, query parse) is paid at most once per request even though properties look free.
**Invariant:** snapshot-at-first-access is a contract, not an optimization detail — code may rely on `request.query_params` being stable across the request lifetime, and must NOT expect mid-request scope writes to appear in already-touched views. The `hasattr` form also survives subclasses that re-derive with different types.
**Probe:** `tests/test_requests.py::test_request_query_params` (:32) + `::test_request_url` (:17) pin derived values; snapshot-vs-live contrast pinned by state tests (`tests/test_requests.py:292-337`, cited in state-scope-write-through).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", filePattern: "*requests*", namePattern: "^(url|base_url|headers|query_params|cookies|state)$", limit: 10 });
```

## Verdict
Adopt compute-once derivation for per-request parsed views — it bounds parsing cost and makes view semantics deterministic. Adapt which properties cache (path_params reads scope fresh each access because it's a plain passthrough :144-147 — cheap keys don't need slots). Omit caching for anything that must track live scope mutations; alias the scope object instead, as State does.
