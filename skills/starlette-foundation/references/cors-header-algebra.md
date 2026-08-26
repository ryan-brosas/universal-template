<!-- capsule-v2 -->
# CORSMiddleware preflight compile-time headers + simple-response origin mirroring

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** Which CORS decisions are precomputed at construction, and why do wildcard-origins-with-credentials responses mirror the request Origin?

## CORSMiddleware.__init__ — preflight header algebra
**Path/Symbol:** `starlette/middleware/cors.py:__init__` (:16-76).
**Data Shape:** booleans `allow_all_origins`, `allow_all_headers`, and the pivotal `preflight_explicit_allow_origin = not allow_all_origins or allow_credentials`.
### Decisive source
```python
if preflight_explicit_allow_origin:
    preflight_headers["Vary"] = "Origin"          # response varies per request origin
else:
    preflight_headers["Access-Control-Allow-Origin"] = "*"
...
allow_headers = sorted(SAFELISTED_HEADERS | set(allow_headers))
if allow_headers and not allow_all_headers:
    preflight_headers["Access-Control-Allow-Headers"] = ", ".join(allow_headers)
```
**Flow:** `"*" in allow_methods` expands to ALL_METHODS tuple (never echoed as literal `*`); safelisted headers are always implicitly allowed so they're merged into the announced list; regex origins compiled once.

## preflight_response — failures list → 400 with policy headers intact
**Path/Symbol:** `starlette/middleware/cors.py:preflight_response` (:107-150).
**Data Shape:** collects failure reasons ("origin", "method", "headers", "private-network"); on ANY failure returns 400 PlainText "Disallowed CORS {reasons}" BUT still carrying computed ACAO/ACAM headers — informative, enforcement is the browser's.
**Flow:** allow_all_headers MIRRORS back `access-control-request-headers` verbatim (:129-130) instead of enumerating; private-network opt-in adds `Access-Control-Allow-Private-Network: true`.
**Invariant:** OPTIONS-without-access-control-request-method is NOT a preflight — it falls through to simple_response (normal app handling).
**Probe:** `tests/middleware/test_cors.py::test_cors_disallowed_preflight` (:171), `::test_preflight_allows_request_origin_if_origins_wildcard_and_credentials_allowed` (:212).

## send wrapper — simple responses
**Path/Symbol:** `starlette/middleware/cors.py:simple_response/send` (:152-174) + static `allow_explicit_origin` (:176-179).
### Decisive source
```python
if self.allow_all_origins and self.allow_credentials:
    self.allow_explicit_origin(headers, origin)      # '*' illegal with credentials → echo
elif not self.allow_all_origins and self.is_allowed_origin(origin):
    self.allow_explicit_origin(headers, origin)
# static:  headers["Access-Control-Allow-Origin"] = origin
#          headers.add_vary_header("Origin")
```
**Flow:** wraps downstream send via functools.partial; only touches `http.response.start`; updates over simple_headers then conditionally mirrors origin + Vary.
**Invariant:** mirroring ALWAYS pairs with Vary: Origin — without it caches serve one origin's CORS headers to another. The wildcard+credentials case is the classic silent breakage this middleware encodes as data.
**Probe:** `::test_cors_allow_all_except_credentials` (:71), `::test_cors_allow_specific_origin` (:122), `::test_cors_allow_all` (:10).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "preflight_response", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "allow_explicit_origin", limit: 5 });
```

## Verdict
Adopt the precompute-at-init design (per-request work shrinks to two dict lookups + a comparison). Adopt the credentials-force-mirror rule and its Vary companion. Adapt SAFELISTED_HEADERS to future spec additions.
