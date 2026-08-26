<!-- capsule-v2 -->
# PreparedRequest prepare order — why must body precede auth, and hooks go last?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What is the fixed stage ordering of `PreparedRequest.prepare` and what breaks when reordered?

## PreparedRequest.prepare
**Path/Symbol:** `src/requests/models.py:PreparedRequest.prepare` (:424-451); per-stage methods :467-729.
**Signature:** `prepare(method=None, url=None, headers=None, files=None, data=None, params=None, auth=None, cookies=None, hooks=None, json=None) -> None`.

### Decisive source
```python
self.prepare_method(method)
self.prepare_url(url, params)
self.prepare_headers(headers)
self.prepare_cookies(cookies)
self.prepare_body(data, files, json)
self.prepare_auth(auth, url)
# Note that prepare_auth must be last to enable authentication schemes
# such as OAuth to work on a fully prepared request.
# This MUST go after prepare_auth. Authenticators could add a hook
self.prepare_hooks(hooks)
```
plus the auth application contract:
```python
r = auth_handler(self)          # auth returns (a copy of) the PreparedRequest
self.__dict__.update(r.__dict__)  # merge mutated state back
# Recompute Content-Length
self.prepare_content_length(self.body)
```

**Flow:** method→url(+params encoding)→headers(validated)→cookies(Cookie header generated ONCE)→body(CL/TE/json/multipart decisions)→auth(sees final URL/headers/body; may mutate anything; Content-Length recomputed after)→hooks(registered last so auth-added hooks survive).
**Invariant:** The two inline comments ARE the invariant: OAuth-style flows sign the fully prepared request (URL query already merged, body bytes finalized), so auth-after-body is mandatory; and hooks register after auth because `HTTPDigestAuth.__call__` itself registers response hooks — earlier hook registration would still work but auth-supplied hooks are guaranteed present. `prepare_cookies` docstring warns it can only run once per PreparedRequest (cookiejar won't regenerate an existing Cookie header) — redirect code pops "Cookie" first precisely for this.
**Probe:** Direct tests: `tests/test_requests.py::test_json_param_post_content_type_works` (:2164) pins body-stage output; digest tests :748+ pin auth-stage behavior; `grep -n "prepare_hooks(hooks)" src/requests/models.py` → 1 hit at final line of prepare (:451).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "PreparedRequest prepare method url headers", limit: 10 });
```

## Verdict
Adopt the seven-stage fixed order with its two documented reasons. Adapt nothing about ordering; adapt stage internals freely. Omit py2 unicode handling inside stages.
