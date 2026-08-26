<!-- capsule-v2 -->
# ASGIRequest header funnel — how do raw ASGI scope headers become WSGI-compatible META without letting spoofed or duplicated headers through?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** When bridging a binary-header protocol (ASGI/HTTP2) into a WSGI-style environ dict, which headers get special names, which are dropped, and how do duplicates merge?

## Scope→META decoding funnel
**Path/Symbol:** `django/core/handlers/asgi.py:ASGIRequest.__init__` (49–116).
**Signature:** `__init__(self, scope, body_file)` — builds `self.META` in one pass over `scope["headers"]`.
**Data Shape:** Input: list of `(bytes name, bytes value)` pairs. Output: META dict with `CONTENT_LENGTH`, `CONTENT_TYPE`, `HTTP_<UPPER_SNAKE>` keys; multi-valued headers comma-joined EXCEPT cookie which is `"; ".join`-ed; underscore-bearing names silently skipped.

### Decisive source
```python
_headers = defaultdict(list)
for name, value in self.scope.get("headers", []):
    name = name.decode("latin1")
    # Prevent spoofing via ambiguity between underscores and hyphens.
    if "_" in name:
        continue
    if name == "content-length":
        corrected_name = "CONTENT_LENGTH"
    elif name == "content-type":
        corrected_name = "CONTENT_TYPE"
    else:
        corrected_name = "HTTP_%s" % name.upper().replace("-", "_")
    value = value.decode("latin1")
    if corrected_name == "HTTP_COOKIE":
        value = value.rstrip("; ")
    _headers[corrected_name].append(value)
if cookie_header := _headers.pop("HTTP_COOKIE", None):
    self.META["HTTP_COOKIE"] = "; ".join(cookie_header)
self.META.update({name: ",".join(value) for name, value in _headers.items()})
```

**Flow:** latin1-decode every pair → drop any name containing `_` (an attacker-sent `X_Forwarded_For` would otherwise alias the trusted `X-Forwarded-For`) → route content-length/content-type to their unprefixed WSGI names → accumulate duplicates → join cookies with `"; "` after stripping trailing separators, everything else with `","`.
**Invariant:** (1) Underscore-in-name rejection happens BEFORE case normalization — it is an anti-aliasing rule, not a style rule. (2) Duplicate `Content-Length` values comma-join into one string (e.g. `"5,5"`), and downstream `HttpRequest.body` deliberately tolerates that by falling back to 0 on int-parse failure — the two ends of this contract must be ported together. (3) Cookies are joined with `"; "` because multiple cookie headers are semantically one header list per RFC 6265 §5.4.
**Probe:** `tests/asgi/tests.py::ASGITest.test_underscores_in_headers_ignored` (:286) + `.test_multiple_cookie_headers_http2` (:800) + `.test_malformed_content_length` (:831) — pin all three behaviors at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "ASGIRequest META HTTP_COOKIE content-length", limit: 10 });
```

## Verdict
Adopt the underscore-rejection and per-header duplicate-join rules in any ASGI/HTTP2→CGI-style bridge; adapt key naming to your platform's conventions; omit the wsgi.multithread/multiprocess flags if not serving WSGI-expecting code. Direct tests cited executed green at this pin.
