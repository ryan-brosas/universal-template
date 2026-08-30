<!-- capsule-v2 -->
# Voyager private-API client — how do I call LinkedIn's internal REST API with cookie auth without tripping security?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c`; Codebase Memory `open-linkedin-api`. **Question:** what exact headers, base URLs, CSRF derivation, and request pacing make `/voyager/api` calls work from a plain requests.Session?

## Client bootstrap and the evade-before-every-request seam
**Path/Symbol:** `open_linkedin_api/client.py:Client` (:19–172), `open_linkedin_api/linkedin.py:Linkedin._fetch/_post` (:84–104).
**Signature:** `Client(*, debug=False, refresh_cookies=False, proxies={}, cookies_dir="")`; `_fetch(uri, evade=default_evade, base_request=False, **kwargs)` / `_post(...)` (same shape).
**Data Shape:** two header sets — `REQUEST_HEADERS` (desktop Chrome UA, `x-li-lang`, `x-restli-protocol-version: 2.0.0`) for API calls vs `AUTH_REQUEST_HEADERS` (`X-Li-User-Agent: LIAuthLibrary…com.linkedin.android`, `User-Agent: ANDROID OS`) only for `/uas/authenticate`. `API_BASE_URL = https://www.linkedin.com/voyager/api`; `base_request=True` switches to the bare host (login/HTML endpoints).

### Decisive source
```python
def _fetch(self, uri, evade=default_evade, base_request=False, **kwargs):
    evade()   # ALWAYS before the request — pacing is part of the transport, not the caller
    url = f"{self.client.API_BASE_URL if not base_request else self.client.LINKEDIN_BASE_URL}{uri}"
    return self.client.session.get(url, **kwargs)

def default_evade():
    sleep(random.randint(2, 5))  # bounded jitter, module-level so any caller shares it
```

**Flow:** build session → set desktop headers → authenticate (android headers) → derive CSRF from cookies → every read/write goes through `_fetch`/`_post`, which sleeps 2–5 s randomly, THEN picks API vs base URL by `base_request`, THEN issues the request.
**Invariant:** the CSRF token is `session.cookies["JSESSIONID"].strip('"')` — quotes MUST be stripped or every call 403s (`_set_session_cookies`, client.py:78–85). Evade runs even when the caller forgets it because it defaults inside the transport signature.
**Probe:** repo ships **no tests** — coverage caveat: claims are source-grounded only (whole file read at HEAD).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "default_evade", limit: 10 });
// resolves: open_linkedin_api.linkedin.default_evade, Client._fetch, Client._post, Client.authenticate
```

## Verdict
Adopt the dual-header split (desktop UA for API / android LIAuthLibrary UA for auth), CSRF-from-JSESSIONID strip, and transport-level evade hook; adapt base URLs, jitter bounds, and proxy wiring to host; omit the GraphQL `queryId` hard-coding (rotates upstream) and the pickled-cookie path (see cookie-session-persistence.md). Direct-test caveat: no tests exist in this repo.
