<!-- capsule-v2 -->
# Response.next lookahead — how does Response.next expose the next redirect target without sending it?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** How is `r._next` populated and what does yield_requests change in resolve_redirects?

## Session.send lookahead + resolve_redirects(yield_requests=True)
**Path/Symbol:** `src/requests/sessions.py:Session.send` (:817-824), `SessionRedirectMixin.resolve_redirects` yield arm (:289-290), `models.py:Response.next` property (:891-894).
**Signature:** `resolve_redirects(..., yield_requests: bool = False, ...)`; `Response.next -> PreparedRequest | None`.

### Decisive source
```python
# sessions.py — when redirects aren't followed:
if not allow_redirects:
    try:
        r._next = next(
            self.resolve_redirects(r, request, yield_requests=True, **kwargs))
            # type: ignore[assignment]  # yield_requests=True returns PreparedRequest
    except StopIteration:
        pass                       # no redirect pending → _next stays None

# sessions.py resolve_redirects:
if yield_requests:
    yield req                      # Internal use only, returns PreparedRequest
else:
    resp = self.send(req, ..., allow_redirects=False, ...)
    extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)
    url = self.get_redirect_target(resp)
    yield resp

# models.py:
@property
def next(self) -> PreparedRequest | None:
    """Returns a PreparedRequest for the next request in a redirect chain."""
    return self._next
```

**Flow:** allow_redirects=False send → generator driven ONE step in request-yield mode → fully rebuilt PreparedRequest (method rewritten per status, cookies merged, auth/proxies rebuilt) lands on `r._next` → user calls `response.next` then `session.send(response.next)` manually → StopIteration (no redirect) leaves None.
**Invariant:** The lookahead performs ALL rebuild work (cookies from the redirect response ARE extracted into session.cookies during this step even though nothing is sent) so `session.send(r.next)` is byte-equivalent to having allowed redirects. Porters who lazily compute `_next` on attribute access lose that side-effect timing; porters who skip StopIteration handling crash non-redirect responses.
**Probe:** Direct tests: `tests/test_requests.py::test_manual_redirect_with_partial_body_read` (:1988, manual next + resolve_redirects interplay), `::test_chunked_upload_does_not_set_content_length_header` (:2275, generator body ⇒ TE header), `::test_custom_redirect_mixin` (:2286+, get_redirect_target override seam); `grep -n "yield_requests" src/requests/sessions.py` → 4 hits (param :195, type-comment :820, yield :290 + docstring).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "yield_requests PreparedRequest redirect", limit: 10 });
```

## Verdict
Adopt eager-lookahead-with-side-effects design. Adapt property name freely. Omit nothing.
