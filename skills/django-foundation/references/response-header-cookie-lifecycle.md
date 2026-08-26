<!-- capsule-v2 -->
# Response headers + cookie lifecycle — how are header values charset-enforced, and when does delete_cookie force secure?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** What invariants must a response header store maintain (encoding, newline injection, case), and what special-casing do cookie deletes need?

## ResponseHeaders codec + cookie FSM
**Path/Symbol:** `django/http/response.py` — `ResponseHeaders` (40–99), `HttpResponseBase.set_cookie` (223–285), `delete_cookie` (297–313), `charset` property (164–177).
**Signature:** `__setitem__(self, key, value)`; `set_cookie(self, key, value="", max_age=None, expires=None, path="/", domain=None, secure=False, httponly=False, samesite=None)`; `delete_cookie(key, path="/", domain=None, samesite=None)`.
**Data Shape:** keys ascii, values latin-1 with MIME `Header(...).encode()` fallback for unencodable chars; `\n`/`\r` anywhere ⇒ `BadHeaderError`; cookies accumulate in a `SimpleCookie` and are serialized per-request by the handlers.

### Decisive source
```python
def __setitem__(self, key, value):
    key = self._convert_to_charset(key, "ascii")
    value = self._convert_to_charset(value, "latin-1", mime_encode=True)
    self._store[key.lower()] = (key, value)      # original case preserved
...
def delete_cookie(self, key, path="/", domain=None, samesite=None):
    # Browsers can ignore the Set-Cookie header if the cookie doesn't use
    # the secure flag and:
    # - the cookie name starts with "__Host-" or "__Secure-", or
    # - the samesite is "none".
    secure = key.startswith(("__Secure-", "__Host-")) or (
        samesite and samesite.lower() == "none")
    self.set_cookie(key, max_age=0, path=path, domain=domain,
                    secure=secure,
                    expires="Thu, 01 Jan 1970 00:00:00 GMT", samesite=samesite)
```

**Flow:** every header write funnels through `_convert_to_charset` → newline check raises before storage (CRLF-injection defense at the API boundary, not at serialization) → case-insensitive lookup but first-seen casing kept on the wire. Cookie sets: datetime expires convert to max_age (+1s rounding); IE needs explicit expires alongside max-age. Cookie deletes: epoch-expires + max_age=0 PLUS forced secure for `__Secure-`/`__Host-` prefixes or `SameSite=none`, because browsers otherwise ignore the deletion.
**Invariant:** (1) Header values are validated at SET time — a bad value surfaces at the code that set it with a traceback, not as a corrupted wire response. (2) `charset` is re-derived from Content-Type each read (never cached into `_charset`) so middleware can switch encoding mid-flight. (3) Delete-cookie must mirror the set-time attributes that gate browser acceptance or the delete silently fails.
**Probe:** `tests/responses/tests.py::HttpResponseTests` (BadHeaderError on CRLF at :117 area) + `tests/responses/test_cookie.py::CookieTests.test_delete_cookie_secure_prefix` (:134) and `.test_delete_cookie_secure_samesite_none` (:147) — direct suites executed green at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "ResponseHeaders set_cookie delete_cookie BadHeaderError", limit: 10 });
```

## Verdict
Adopt set-time charset enforcement + prefix-aware deletion for any HTTP response layer; adapt charsets to your platform's header encoding rules; omit MIME-encoded fallback if your values are guaranteed ASCII/latin-1. Direct suites cited executed green at this pin.
