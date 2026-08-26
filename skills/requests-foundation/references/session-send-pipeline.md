<!-- capsule-v2 -->
# Session send orchestration — what is the exact pipeline from PreparedRequest to history-assembled Response?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** In `Session.send`, in what order do adapter dispatch, elapsed timing, hooks, cookie extraction, redirect resolution, and content consumption run?

## Session.send
**Path/Symbol:** `src/requests/sessions.py:Session.send` (:752-829).
**Signature:** `send(request: PreparedRequest, **kwargs) -> Response`.
**Data Shape:** kwargs carry stream/verify/cert/proxies (defaults filled from session + resolve_proxies), allow_redirects, timeout.

### Decisive source
```python
if isinstance(request, Request):
    raise ValueError("You can only send PreparedRequests.")
adapter = self.get_adapter(url=request.url)
start = preferred_clock()
r = adapter.send(request, **kwargs)
elapsed = preferred_clock() - start
r.elapsed = timedelta(seconds=elapsed)
r = dispatch_hook("response", hooks, r, **kwargs)
if r.history:                       # hooks may create history — take their cookies too
    for resp in r.history:
        extract_cookies_to_jar(self.cookies, resp.request, resp.raw)
extract_cookies_to_jar(self.cookies, request, r.raw)
if allow_redirects:
    gen = self.resolve_redirects(r, request, **kwargs)
    history = [resp for resp in gen]
else:
    history = []
if history:
    history.insert(0, r); r = history.pop(); r.history = history
if not allow_redirects:
    try:
        r._next = next(self.resolve_redirects(r, request, yield_requests=True, **kwargs))
    except StopIteration:
        pass
if not stream:
    r.content                       # force consumption when not streaming
```

**Flow:** reject un-prepared Request → pick adapter by URL prefix → time ONLY the adapter call into `r.elapsed` → response hooks run BEFORE cookies/history exist → cookie extraction covers hook-created history then the live response → redirect generator drives further hops (each hop re-extracts cookies) → final assembly rotates the last response to the front with full history → when redirects disabled, one lookahead step is stored on `r._next` so `Response.next` works without sending → non-streaming forces `.content` to free the connection before returning.
**Invariant:** Hooks observe the response BEFORE cookies are persisted and BEFORE redirects resolve — a hook mutating status/location changes redirect behavior itself. `elapsed` measures adapter time only (excludes preparation/hooks). The `preferred_clock` shim (perf_counter on win32, time.time elsewhere) exists for timeout-resolution accuracy. Porters who extract cookies after redirect assembly lose per-hop Set-Cookie state; porters who skip the `isinstance(request, Request)` guard give users a confusing deep stack instead of the contract error.
**Probe:** Direct tests: `tests/test_requests.py::test_requests_in_history_are_not_overridden` (:482), `::test_requests_history_is_saved` (:2153), `::test_session_pickling` (:1619) pins `__attrs__` persistence around send. `grep -n "preferred_clock" src/requests/sessions.py` → 4 hits (defs :70-73 + uses :781/:787).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "preferred_clock Session.send adapter", limit: 10 });
```

## Verdict
Adopt the stage ordering verbatim. Adapt hook names and timing clock to host. Omit the deprecated `session()` factory.
