<!-- capsule-v2 -->
# Voyager password-auth + metadata bootstrap — how do I authenticate to the private API with username/password (not a browser) and classify the failure states?

**Source:** open-linkedin-api MIT `main@5feee360ec26719d07d5e67638045e751b48a74c` (`client.py`, `settings.py`); Codebase Memory `open-linkedin-api`. **Question:** what is the API-side password-auth flow — the `/uas/authenticate` POST, the `login_result` PASS gate, the distinct exception classes, and the meta-tag metadata bootstrap — and how does it differ from the browser login ladder?

## Client.authenticate + _do_authentication_request + _fetch_metadata
**Path/Symbol:** `client.py:Client` (:19–172) — `authenticate` (:91–102), `_do_authentication_request` (:138–172), `_fetch_metadata` (:104–136), `_set_session_cookies` (:78–85), `_request_session_cookies` (:65–76); `settings.py` (:1–7) for the cookie dir.
**Signature:** `Client(*, debug=False, refresh_cookies=False, proxies={}, cookies_dir="")`; `authenticate(username, password)`; `_do_authentication_request(username, password)`; `_fetch_metadata()`.
**Data Shape:** two header sets — `AUTH_REQUEST_HEADERS` (`X-Li-User-Agent: LIAuthLibrary:0.0.3 com.linkedin.android...`, `User-Agent: ANDROID OS`) used ONLY for `/uas/authenticate` and the metadata GET; `REQUEST_HEADERS` (desktop Chrome UA, `x-li-lang`, `x-restli-protocol-version: 2.0.0`) for API calls. The auth POST body is `{session_key, session_password, JSESSIONID}`. Failure classes: `ChallengeException(login_result)` for a non-PASS `login_result`, `UnauthorizedException` for HTTP 401, generic `Exception` for any other non-200.

### Decisive source
```python
def _do_authentication_request(self, username, password):
    self._set_session_cookies(self._request_session_cookies())   # seed a fresh JSESSIONID first
    payload = {"session_key": username, "session_password": password,
               "JSESSIONID": self.session.cookies["JSESSIONID"]}
    res = requests.post(f"{Client.LINKEDIN_BASE_URL}/uas/authenticate",
                        data=payload, cookies=self.session.cookies,
                        headers=Client.AUTH_REQUEST_HEADERS, proxies=self.proxies)
    data = res.json()
    if data and data["login_result"] != "PASS":
        raise ChallengeException(data["login_result"])     # e.g. "CHALLENGE"/"FAIL" — distinct class
    if res.status_code == 401:
        raise UnauthorizedException()
    if res.status_code != 200:
        raise Exception()
    self._set_session_cookies(res.cookies)                 # now authenticated cookies
    self._cookie_repository.save(res.cookies, username)

def _fetch_metadata(self):
    res = requests.get(f"{Client.LINKEDIN_BASE_URL}", cookies=self.session.cookies,
                       headers=Client.AUTH_REQUEST_HEADERS, proxies=self.proxies)
    soup = BeautifulSoup(res.text, "lxml")
    # meta[name=applicationInstance] → self.metadata["clientApplicationInstance"]
    # meta[name=clientPageInstanceId]  → self.metadata["clientPageInstanceId"]
```

**Flow:** `authenticate` → cache-first (cookie-session-persistence.md) else `_do_authentication_request`: seed a fresh JSESSIONID from a GET to `/uas/authenticate`, POST credentials + that JSESSIONID, gate on `login_result == "PASS"` (raise `ChallengeException` otherwise), raise `UnauthorizedException` on 401, generic on other non-200, then set the authenticated cookies + save the jar. Finally `_fetch_metadata` GETs the homepage and scrapes `meta[name=applicationInstance]` and `meta[name=clientPageInstanceId]` into `self.metadata` for later API calls.
**Invariant:** the `login_result` JSON field is the authoritative auth gate — a non-`PASS` value (challenge/FAIL) raises `ChallengeException` carrying the raw result, BEFORE the HTTP-status checks. The `JSESSIONID` must be seeded from a prior GET (you cannot POST credentials without a session cookie). The auth request uses the *android* `AUTH_REQUEST_HEADERS`, never the desktop API headers. Metadata bootstrap is a separate homepage GET that must succeed after auth (it feeds `clientApplicationInstance` to later requests).
**Probe:** no upstream tests for the auth flow — coverage caveat recorded; behavior pinned by reading client.py:65–172 at HEAD. Graph anchors resolve `Client._do_authentication_request`, `Client._fetch_metadata`, `Client.authenticate`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "_do_authentication_request", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "open-linkedin-api", query: "_fetch_metadata", limit: 10 });
```

## Verdict
Adopt the seed-JSESSIONID-then-POST flow, the `login_result == "PASS"` gate with a distinct `ChallengeException`, the android-header auth split, and the meta-tag metadata bootstrap; adapt the cookie dir (`settings.COOKIE_PATH` → `~/.linkedin_api/cookies/`), exception names, and the metadata meta names (rotate) to host; omit the pickled-cookie persistence (see cookie-session-persistence.md) and the hard-coded UA strings. Caveat: source-grounded only, no test coverage.
