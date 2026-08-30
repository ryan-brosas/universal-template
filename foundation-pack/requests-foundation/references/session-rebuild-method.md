<!-- capsule-v2 -->
# Redirect method rewriting — which status codes downgrade POST to GET, and why does HEAD stay HEAD?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What method-rewrite matrix does `rebuild_method` apply per redirect status?

## SessionRedirectMixin.rebuild_method
**Path/Symbol:** `src/requests/sessions.py:SessionRedirectMixin.rebuild_method` (:370-392).
**Signature:** `rebuild_method(prepared_request: PreparedRequest, response: Response) -> None`.

### Decisive source
```python
# https://tools.ietf.org/html/rfc7231#section-6.4.4
if response.status_code == codes.see_other and method != "HEAD":
    method = "GET"          # 303 always becomes GET (except HEAD)
# Do what the browsers do, despite standards...
if response.status_code == codes.found and method != "HEAD":
    method = "GET"          # 302 -> GET (browser behavior over RFC)
if response.status_code == codes.moved and method == "POST":
    method = "GET"          # 301 downgrades POST only (Issue 1704)
prepared_request.method = method
```

**Flow:** 303 → GET for everything except HEAD → 302 → GET for everything except HEAD → 301 → GET only when method was POST.
**Invariant:** The matrix is deliberately browser-compatible, NOT RFC-compliant: 302/303 rewrite ANY non-HEAD method (PUT/DELETE included), while 301 rewrites ONLY POST — a POST→GET on 301 but PUT survives 301. 307/308 never reach this method (they're excluded from the body-purge branch in resolve_redirects AND have no rewrite arm), so body+method survive intact only for those. HEAD is preserved through every downgrade so `Session.head(allow_redirects=True)` stays HEAD end-to-end (`tests/test_requests.py::test_http_303_doesnt_change_head_to_get`).
**Probe:** Direct tests (httpbin live, `TestRequests` class): `test_http_303_changes_post_to_get` (:306), `test_http_303_doesnt_change_head_to_get` (:313), plus 301/302 variants nearby; `grep -c "method = \"GET\"" src/requests/sessions.py` → 3.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "rebuild_method see_other found moved", limit: 10 });
```

## Verdict
Adopt the exact three-arm matrix with its HEAD exemption. Adapt status-code constants to host enums. Omit any auth-int/qop logic (none here).
