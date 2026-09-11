<!-- capsule-v2 -->
# Basic-auth encoding — what exact bytes go on the wire for `HTTPBasicAuth`, and how are odd inputs coerced?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `requests`. **Question:** Which encoding converts username/password into the Authorization header, and what is the compatibility behavior for non-str/bytes credentials?

## auth._basic_auth_str / HTTPBasicAuth / HTTPProxyAuth
**Path/Symbol:** `src/requests/auth.py:_basic_auth_str` (:34-75), `AuthBase.__call__` (:81-82), `HTTPBasicAuth` (:85-113), `HTTPProxyAuth` (:116-121).
**Signature:** `_basic_auth_str(username: bytes | str, password: bytes | str) -> str`; `HTTPBasicAuth.__call__(r: PreparedRequest) -> PreparedRequest`.
**Data Shape:** output is a single native-str header value `"Basic <b64>"`; inputs accept str or bytes (plus a deprecated anything-else shim).

### Decisive source
```python
if not isinstance(username, basestring):        # compat shim (removal planned 3.0)
    warnings.warn("Non-string usernames will no longer be supported ...",
                  category=DeprecationWarning)
    username = str(username)
...same for password...

if isinstance(username, str):
    username = username.encode("latin1")        # NOT utf-8 — deliberate
if isinstance(password, str):
    password = password.encode("latin1")

authstr = "Basic " + to_native_string(
    b64encode(b":".join((username, password))).strip()
)

# HTTPBasicAuth.__call__:
r.headers["Authorization"] = _basic_auth_str(self.username, self.password)
return r
# HTTPProxyAuth.__call__: identical but writes "Proxy-Authorization"
```

**Flow:** non-string credentials warn + str() → any str halves are encoded **latin-1** (bytes pass through untouched) → `user:pass` joined with a raw colon byte and base64-encoded → prefixed `"Basic "` as a NATIVE string → auth callable mutates the prepared request's header dict in place and returns it so hook chaining sees the same object.
**Invariant:** latin-1 is the wire contract — UTF-8 credentials containing codepoints >U+00FF raise UnicodeEncodeError here rather than silently producing a server-incompatible header; bytes inputs skip re-encoding entirely. Value equality (`__eq__` compares username+password via getattr-defaults) makes two HTTPBasicAuth instances interchangeable in session-auth comparisons. Empty password yields the canonical `user:` b64 with trailing padding (`dXNlcjo=`), pinned byte-for-byte.
**Probe:** Direct tests: `tests/test_requests.py::test_basic_auth_str_is_always_native` (:2148-2151, parametrized str/bytes arms asserting `builtin_str` type + exact value), `::test_proxy_auth` (:2220-2223, `"Basic dXNlcjpwYXNz"` via adapter.proxy_headers), `::test_proxy_auth_empty_pass` (:2225-2228, `"Basic dXNlcjo="`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "requests", query: "basic auth b64encode latin", limit: 10 });
```

## Verdict
Adopt latin-1 + colon-join + native-str wrapper exactly; keep the deprecation shim only if your API historically accepted ints. Adapt header-name selection (Authorization vs Proxy-Authorization) via subclass override like HTTPProxyAuth. Omit nothing else.
