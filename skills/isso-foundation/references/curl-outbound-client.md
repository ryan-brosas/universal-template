<!-- capsule-v2 -->
# curl helper — how does the server talk back to the commented site?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What are the retry/redirect semantics of the outbound HTTP client used for title fetching and startup checks?

## http.curl context manager
**Path/Symbol:** `isso/utils/http.py:curl` (lines 12–60).
**Signature:** `curl(method, host, path, timeout=3)` used as `with ... as resp:`; yields response or None.
**Data Shape:** UA = `Isso/<version> (+https://isso-comments.de)`; MAX_RETRY_COUNT=3 loop over connection attempts.

### Decisive source
```python
for _ in range(MAX_RETRY_COUNT):
    self.con = http(host, port, timeout=self.timeout)
    try:
        self.con.request(self.method, self.path, headers=self.headers)
    except (httplib.HTTPException, socket.error):
        return None
    try:
        resp = self.con.getresponse()
        if resp.status == 301:
            location = resp.getheader("Location")
            if location:
                self.con.close()
                self.path = urlparse(location).path
            else:
                return None
        else:
            return resp
    except (httplib.HTTPException, socket.timeout, socket.error):
        return None
```

**Flow:** per attempt: connect+send (failure → None immediately) → 301 rewrites ONLY the path component and retries on a fresh connection → any other status returns the response object for status inspection by the caller (`new` checks `resp.status == 200`; make_app only logs).
**Invariant:** The client never raises — every failure mode collapses to `None`, so callers MUST null-check. Redirect handling is path-only (scheme/host changes are ignored) which keeps title fetching pinned to the validated origin host. Tests monkeypatch this class wholesale (`http.curl = curl` fixture) to keep view tests offline.
**Probe:** `grep -c MAX_RETRY_COUNT isso/utils/http.py` (`2`); anchor for UA header: `grep -n 'Isso/{0}' isso/utils/http.py | wc -l` (`1`).
**Test:** replaced via fixtures.py in all view suites (offline determinism — direct coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "curl httplib 301 Location timeout", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt never-raising context-manager clients at boundaries where absence is an expected outcome. Adapt retry policy. Omit path-only redirect handling if your callers need cross-host follow (then re-validate origins!).
