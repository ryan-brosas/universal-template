<!-- capsule-v2 -->
# Redirect resolution loop — how does requests follow redirects while draining sockets, capping hops, and preserving history?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What is the exact per-hop choreography of `resolve_redirects`, and which invariants keep pooled connections from leaking?

## SessionRedirectMixin.resolve_redirects
**Path/Symbol:** `src/requests/sessions.py:SessionRedirectMixin.resolve_redirects` (:186-307).
**Signature:** `resolve_redirects(resp, req, stream=False, timeout=None, verify=True, cert=None, proxies=None, yield_requests=False, **adapter_kwargs) -> Generator[Response | PreparedRequest]`.
**Data Shape:** Consumes the first Response + its PreparedRequest; yields each subsequent Response (or the next PreparedRequest when `yield_requests=True` — this is what powers `Response.next`).

### Decisive source
```python
while url:
    prepared_request = req.copy()
    resp.history = hist[:]
    hist.append(resp)
    try:
        resp.content            # Consume socket so it can be released
    except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
        resp.raw.read(decode_content=False)
    if len(resp.history) >= self.max_redirects:
        raise TooManyRedirects(f"Exceeded {self.max_redirects} redirects.", response=resp)
    resp.close()                # Release the connection back into the pool
    ...
    headers.pop("Cookie", None)          # rebuilt below from the jar
    extract_cookies_to_jar(cookie_jar, req, resp.raw)
    merge_cookies(cookie_jar, self.cookies)
    prepared_request.prepare_cookies(cookie_jar)
    proxies = self.rebuild_proxies(prepared_request, proxies)
    self.rebuild_auth(prepared_request, resp)
    rewindable = prepared_request._body_position is not None and (
        "Content-Length" in headers or "Transfer-Encoding" in headers)
    if rewindable:
        rewind_body(prepared_request)
```

**Flow:** get target → copy request → record history → FORCE-consume prior body (falling back to raw read on decode errors so a poisoned stream still frees the socket) → enforce `max_redirects` (default 30, `models.DEFAULT_REDIRECT_LIMIT`) → close response → normalize scheme-less `//host/path`, reattach previous fragment unless new one present, urljoin+requote relative locations → rebuild method/cookies/proxies/auth → rewind file bodies → send with `allow_redirects=False`.
**Invariant:** The socket-drain ladder (`resp.content` then fallback `resp.raw.read(decode_content=False)` then `resp.close()`) is what returns connections to the urllib3 pool — porters who skip the drain hang the pool under keep-alive. History mutation is positional: `resp.history = hist[:]` BEFORE append means each intermediate response carries exactly its predecessors; final assembly in `Session.send` inserts the original first and pops the last (`tests/test_requests.py::test_requests_history_is_saved` pins prefix-growth). Body purge only for non-307/308 statuses; Cookie header always popped and rebuilt from the jar (never trusted across hops).
**Probe:** Direct tests: `tests/test_requests.py::test_header_and_body_removal_on_redirect` (:320), `::test_transfer_enc_removal_on_redirect` (:337, generator body ⇒ TE header), `::test_manual_redirect_with_partial_body_read` (:1988, partial iter_content then next(gen)), `::test_fragment_maintained_on_redirect` (:360), `::test_requests_in_history_are_not_overridden` (:482), `::test_redirect_history_no_self_reference` (:220). `grep -c "purged_headers = (" src/requests/sessions.py` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "resolve_redirects history TooManyRedirects", limit: 10 });
```

## Verdict
Adopt the drain-then-close ordering, history slicing, and fragment carry rules verbatim. Adapt max_redirects plumbing to host config. Omit the latin1 location-header re-encode only if your HTTP stack never decodes headers as latin1.
