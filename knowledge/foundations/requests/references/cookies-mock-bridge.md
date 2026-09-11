<!-- capsule-v2 -->
# Cookie jar bridging — how does requests adapt urllib3 responses to http.cookiejar via MockRequest/MockResponse?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What must a MockRequest wrapper implement for stdlib CookieJar extract/add to work against PreparedRequest?

## cookies.MockRequest / MockResponse / extract_cookies_to_jar / get_cookie_header
**Path/Symbol:** `src/requests/cookies.py:MockRequest` (:31-111), `src/requests/cookies.py:MockResponse` (:114-132), `src/requests/cookies.py:extract_cookies_to_jar` (:135-150), `src/requests/cookies.py:get_cookie_header` (:153-161).
**Signature:** `extract_cookies_to_jar(jar: CookieJar, request: PreparedRequest, response) -> None`; `get_cookie_header(jar, request) -> str | None`.

### Decisive source
```python
def extract_cookies_to_jar(jar, request, response):
    if not (hasattr(response, "_original_response") and response._original_response):
        return                          # urllib3 mock/test responses carry no httplib msg
    req = MockRequest(request)
    res = MockResponse(response._original_response.msg)   # raw HTTPMessage headers
    jar.extract_cookies(res, req)

class MockRequest:
    def get_full_url(self):
        # Only return the response's URL if the user hadn't set the Host header
        if not self._r.headers.get("Host"):
            return self._r.url
        host = to_native_string(self._r.headers["Host"], encoding="utf-8")
        parsed = urlparse(self._r.url)
        return urlunparse([parsed.scheme, host, parsed.path,
                           parsed.params, parsed.query, parsed.fragment])
    def add_unredirected_header(self, name, value):
        self._new_headers[name] = value     # Cookie lands here; read back via get_new_headers()
```

**Flow:** guard on `_original_response` (stdlib http.client response hanging off urllib3's) → wrap PreparedRequest as a urllib2-shaped request (type=scheme, host=netloc, unverifiable=True) → hand raw HTTPMessage to jar.extract_cookies → jar policy decides domain/path rules → outgoing direction: `jar.add_cookie_header(mock)` writes Cookie into `_new_headers`, retrieved by `get_new_headers().get("Cookie")`.
**Invariant:** The Host-header reconstruction in `get_full_url` keeps virtual-host cookie scoping correct when users override Host manually. `add_header` deliberately raises — cookiejar MUST use `add_unredirected_header`, anything else means you wired the wrong API. The `_original_response` guard makes the whole bridge no-op-safe on fabricated Responses (tests construct Response with BytesIO raw and no `_original_response`) — porters who unconditionally dereference it crash on synthetic responses.
**Probe:** Direct tests: `tests/test_requests.py::test_manual_redirect_with_partial_body_read` region class TestRedirects cookie-jar preservation test at :455-479 asserts `prep_req._cookies` STAYS a plain cookielib.CookieJar through redirects; `grep -n "_original_response" src/requests/cookies.py` → 1 hit.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "extract_cookies_to_jar MockRequest", limit: 10 });
```

## Verdict
Adopt the two-mock adapter pattern wholesale — it's the canonical way to bolt stdlib cookiejar onto any HTTP client. Adapt the urllib2 attribute surface to whatever your cookiejar expects. Omit nothing; the guards are load-bearing.
