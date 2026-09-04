<!-- capsule-v2 -->
# SessionMiddleware signed-cookie lifecycle — accessed/modified tracking and the clear-then-empty case

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** When does the session cookie get set, cleared, or left alone, and what does `request.session` access do to response headers?

## Session dict subclass — dirty flags via overrides
**Path/Symbol:** `starlette/middleware/sessions.py:Session` (:91-126).
**Data Shape:** class attrs `accessed: bool`, `modified: bool`; EVERY mutation dunder (`__setitem__`, `__delitem__`, `clear`, `update`, `setdefault`) calls `mark_modified()`; `pop` sets modified ONLY if key existed (pop of absent key isn't a change); `mark_accessed` is called by `HTTPConnection.session` property on READ.
**Invariant:** read-tracking exists solely to emit `Vary: Cookie` so caches don't serve one user's personalized response to another.
**Probe:** `tests/middleware/test_session.py::test_session_tracks_modification` (:251), `::test_vary_cookie_on_access` (:227).

## SessionMiddleware.__call__ — unsign → dispatch → conditional Set-Cookie
**Path/Symbol:** `starlette/middleware/sessions.py:SessionMiddleware.__call__` (:39-88).
### Decisive source
```python
try:
    data = self.signer.unsign(data, max_age=self.max_age)   # TimestampSigner = freshness + integrity
    scope["session"] = Session(json.loads(b64decode(data)))
    initial_session_was_empty = False
except BadSignature:
    scope["session"] = Session()          # tampered cookie == fresh empty session (no error!)
...
if session.modified and session:                       # non-empty + changed  → SET
    ...sign(b64encode(json.dumps(session)))... headers.append("Set-Cookie", ...)
elif session.modified and not initial_session_was_empty:  # emptied but was present → EXPIRE
    header_value = "...session_cookie=null; expires=Thu, 01 Jan 1970 00:00:00 GMT..."
```

**Flow:** cookie value = base64(json) signed by itsdangerous TimestampSigner with max_age rechecked at unsign (server-side expiry without server storage). BadSignature (tampered OR expired) silently yields an empty session — never a 400. The three-way outcome at response time: modified+non-empty → set; modified+emptied-with-prior-cookie → delete via null+epoch-expires; unmodified → no cookie work at all.
**Invariant:** clearing a session you never had must NOT emit a deletion cookie (the `not initial_session_was_empty` guard) — otherwise every anonymous visitor gets a junk Set-Cookie.
**Probe:** `::test_set_cookie_only_on_modification` (:207), `::test_invalid_session_cookie` (:144), `::test_session_expires` (:65).

## Cookie attribute string assembly
**Path/Symbol:** `starlette/middleware/sessions.py:__init__` security_flags (:33-37) + format strings (:68-74).
**Data Shape:** `security_flags = "httponly; samesite=lax"` (+ `; secure` if https_only, + `; domain=...` if given); max_age rendered as `Max-Age={n}; ` only when truthy. Note: uses raw `headers.append("Set-Cookie", ...)` NOT Response.set_cookie — because there's no Response object here, just ASGI messages (MutableHeaders(scope=message)).
**Probe:** `::test_secure_session` (:89), `::test_domain_cookie` (:185).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "mark_modified", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "Session", limit: 10 });
```

## Verdict
Adopt flag-tracked dict + three-way cookie lifecycle verbatim (works for any client-side-session framework). Adapt signer choice (itsdangerous) to your crypto stack but keep max_age-at-unsign. Omit websocket scope support only if sessions are HTTP-only in your app.
