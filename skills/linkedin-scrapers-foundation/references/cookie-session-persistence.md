<!-- capsule-v2 -->
# Cookie/session persistence — how do I survive restarts and detect expiry without re-login?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c`; Codebase Memory `open-linkedin-api`. **Question:** what is the minimal correct contract for caching an authenticated LinkedIn session to disk, validating it, and failing loudly when stale?

## CookieRepository + authenticate cache-first flow
**Path/Symbol:** `open_linkedin_api/cookie_repository.py:CookieRepository` (:19–70, `_is_token_still_valid` :61–70); `open_linkedin_api/client.py:Client.authenticate` (:91–102) and `_set_session_cookies` (:78–85).
**Signature:** `save(cookies: RequestsCookieJar, username: str)`; `get(username) -> Optional[RequestsCookieJar]` (raises `LinkedinSessionExpired`); static `_is_token_still_valid(cookiejar) -> bool`.
**Data Shape:** one pickle per account at `{dir}/{username}.jr`; validity = the `JSESSIONID` cookie exists, has a value, AND `cookie.expires > now` (any other cookie is irrelevant).

### Decisive source
```python
def get(self, username):
    cookies = self._load_cookies_from_cache(username)
    if cookies and not CookieRepository._is_token_still_valid(cookies):
        raise LinkedinSessionExpired          # LOUD failure on stale cache — never silently re-login
    return cookies

def authenticate(self, username, password):
    if self._use_cookie_cache:
        cookies = self._cookie_repository.get(username)
        if cookies:
            self._set_session_cookies(cookies)   # sets session.cookies AND csrf header
            self._fetch_metadata()
            return                               # password never sent
    self._do_authentication_request(username, password)
```

**Flow:** authenticate → try cache → valid JSESSIONID? set cookies+CSRF and skip credentials entirely → else full `/uas/authenticate` POST → save fresh jar keyed by username.
**Invariant:** three-way contract — (1) cache hit must restore the CSRF header too (`_set_session_cookies` does both), (2) expired-but-present cache raises instead of falling back (prevents surprise credential use / checkpoint triggers), (3) missing file returns None (first login). Contrast joeyism's browser variant: Playwright `storage_state()` JSON with a session-file fixture that SKIPS tests when absent (tests/conftest.py:44–53).
**Probe:** no unit tests in-repo for this seam — coverage caveat recorded; behavior boundary pinned by reading client.py:91–102 + cookie_repository.py:35–40 at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "CookieRepository", limit: 10 });
// resolves CookieRepository.save/get/_is_token_still_valid + Client.authenticate/_set_session_cookies
```

## Verdict
Adopt cache-first authentication with loud expiry signal and username-keyed jars; adapt storage format (pickle→JSON storage_state in browser contexts), directory, and expiry cookie name to host; omit the TODO FileCookieJar refactor and metadata scraping. Caveat: no direct test pins the expiry path.
