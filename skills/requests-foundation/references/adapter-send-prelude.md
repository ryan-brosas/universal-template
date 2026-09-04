<!-- capsule-v2 -->
# Send prelude — how do chunked detection and timeout coercion run before urlopen?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What exact transformations does HTTPAdapter.send apply to body-chunking and timeout before calling conn.urlopen?

## HTTPAdapter.send prelude
**Path/Symbol:** `src/requests/adapters.py:HTTPAdapter.send` :661-708 (prelude), urlopen call at :696-708.
**Signature:** within `send(request, stream=False, timeout=None, verify=True, cert=None, proxies=None)`.

### Decisive source
```python
chunked = not (request.body is None or "Content-Length" in request.headers)

if isinstance(timeout, tuple):
    try:
        connect, read = timeout
        resolved_timeout = TimeoutSauce(connect=connect, read=read)
    except ValueError:
        raise ValueError(
            f"Invalid timeout {timeout}. Pass a (connect, read) timeout tuple, "
            f"or a single float to set both timeouts to the same value.")
elif isinstance(timeout, TimeoutSauce):
    resolved_timeout = timeout
else:
    resolved_timeout = TimeoutSauce(connect=timeout, read=timeout)
...
resp = conn.urlopen(method=request.method, url=url, body=request.body,
                    headers=request.headers,
                    redirect=False, assert_same_host=False,
                    preload_content=False, decode_content=False,
                    retries=self.max_retries, timeout=resolved_timeout,
                    chunked=chunked)
```

**Flow:** chunked iff body exists AND no Content-Length header (prepare_body normally sets CL or TE header first — this is the fallback for bodies whose length is unknowable) → tuple timeout unpacked strictly 2-ary into connect/read → urllib3 Timeout passthrough → scalar fans to both fields → urlopen pinned with redirect=False (requests owns redirects at Session level), assert_same_host=False (pool may serve any host key it derived), preload_content=False + decode_content=False (streaming contract; Response.raw consumers opt into decoding).
**Invariant:** The four urlopen flags are the adapter↔session contract: redirect=False prevents double redirect handling, the two False loads keep `Response.iter_content` the single decode/consumption point. A porter who leaves preload_content=True silently breaks stream=True memory guarantees. LocationValueError from connection derivation maps to InvalidURL (caught just above at :665-666).
**Probe:** Direct tests: `tests/test_requests.py::test_stream_timeout` (:2537 pins raw-not-preloaded behavior mid-stream), `::test_prepare_request_with_bytestring_url` (:1256); tuple-timeout error text ("Pass a (connect, read) timeout tuple") asserted in timeout ValueError tests. `grep -n "preload_content=False" src/requests/adapters.py` → exactly 1 hit (:703).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "TimeoutSauce chunked urlopen redirect=False", limit: 10 });
```

## Verdict
Adopt the chunked predicate, strict 2-tuple timeout error, and the four urlopen flags as one inseparable unit. Adapt TimeoutSauce to host's timeout type. Omit nothing — flags are behavioral.
