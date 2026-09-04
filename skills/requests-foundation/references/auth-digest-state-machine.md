<!-- capsule-v2 -->
# Digest auth state machine — how does HTTPDigestAuth answer a 401 once, count nonces per-thread, and resend via r.connection?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What is the challenge-response choreography of HTTPDigestAuth including its hook registration and body rewind?

## auth.HTTPDigestAuth
**Path/Symbol:** `src/requests/auth.py:HTTPDigestAuth.__call__` (:321-343), `.handle_401` (:273-319), `.handle_redirect` (:268-271), `.build_digest_header` (:157-266), `_basic_auth_str` (:34-75).
**Signature:** `__call__(r: PreparedRequest) -> PreparedRequest`; `handle_401(r: Response, **kwargs) -> Response`.
**Data Shape:** ALL mutable state in `threading.local` (`last_nonce`, `nonce_count`, `chal`, `pos`, `num_401_calls`) initialized lazily by `init_per_thread_state`.

### Decisive source
```python
def __call__(self, r):
    self.init_per_thread_state()
    if self._thread_local.last_nonce:          # cached nonce → skip the 401 round-trip
        _digest_auth = self.build_digest_header(r.method, r.url)
        if _digest_auth:
            r.headers["Authorization"] = _digest_auth
    if (tell := getattr(r.body, "tell", None)) is not None:
        self._thread_local.pos = tell()        # remember body offset for later rewind
    else:
        self._thread_local.pos = None
    r.register_hook("response", self.handle_401)
    r.register_hook("response", self.handle_redirect)
    self._thread_local.num_401_calls = 1

def handle_401(self, r, **kwargs):
    if not 400 <= r.status_code < 500:
        self._thread_local.num_401_calls = 1
        return r                               # only 4xx triggers auth (issue #3772)
    if self._thread_local.pos is not None:     # rewind streamed body before resend
        if (seek := getattr(r.request.body, "seek", None)) is not None:
            seek(self._thread_local.pos)
    if "digest" in s_auth.lower() and self._thread_local.num_401_calls < 2:
        self._thread_local.num_401_calls += 1  # ONE retry max — wrong creds fail fast
        ...
        r.content; r.close()                   # consume + release for connection reuse
        prep = r.request.copy()
        ...re-extract cookies onto prep...
        prep.headers["Authorization"] = self.build_digest_header(prep.method, prep.url)
        _r = r.connection.send(prep, **kwargs) # resend through SAME adapter/pool
        _r.history.append(r)
        _r.request = prep
        return _r
```

**Flow:** first call: no nonce → register hooks, record body position → response hook fires on 4xx with digest WWW-Authenticate and num_401_calls<2 → consume+close response → copy prepared request, refresh cookies from the 401 response, compute Authorization → RESEND via `r.connection.send` (adapter back-reference from build_response) → returned response gets the 401 appended to ITS history. Subsequent calls short-circuit using last_nonce. handle_redirect resets num_401_calls on redirect hops.
**Invariant:** Per-thread state is mandatory (nonce_count is shared-nothing across threads); num_401_calls<2 caps retries at ONE attempt so bad credentials return the 401 instead of looping. The 4xx-only gate prevents auth attempts on 3xx/5xx. `_basic_auth_str` encodes latin-1 with deprecation warnings for non-str types ("dumb but preserved" back-compat).
**Probe:** Direct tests: `tests/test_requests.py::TestRequests::test_DIGEST_*` family :748-817 (test_DIGEST_HTTP_200_OK_GET :748, test_DIGEST_AUTH_RETURNS_COOKIE :765, test_DIGEST_STREAM :783, test_DIGESTAUTH_WRONG_HTTP_401_GET :794, test_DIGESTAUTH_QUOTES_QOP_VALUE :810) against httpbin digest-auth endpoint; basic-auth native-string matrix at :2140-2154. `grep -n "num_401_calls" src/requests/auth.py` → 9 hits (:134 annotation, :155 init, :269/:271 handle_redirect, :283/:293/:294/:318 handle_401, :341 __call__).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "HTTPDigestAuth thread_local nonce 401", limit: 10 });
```

## Verdict
Adopt hook-driven one-shot retry, threading.local partitioning, and the r.connection.send resend path. Adapt algorithm set (MD5/SHA/SHA-256/SHA-512 supported; MD5-SESS computed; auth-int unimplemented returns None). Omit py2 int-username shims once host drops legacy callers.
