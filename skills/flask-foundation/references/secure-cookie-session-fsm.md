<!-- capsule-v2 -->
# Secure cookie session FSM — when is a cookie read, written, refreshed, or deleted?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What are the exact open/save rules of the default itsdangerous-backed session interface?

## SecureCookieSessionInterface open/save decision tree
**Path/Symbol:** `src/flask/sessions.py:SecureCookieSessionInterface` (284–385); `SessionMixin` flags (24–54); `NullSession` (83–97).
**Signature:** `open_session(app, request) -> SecureCookieSession|None`; `save_session(app, session, response) -> None`; `get_signing_serializer(app) -> URLSafeTimedSerializer|None`.
**Data Shape:** serializer = TaggedJSONSerializer payload inside URLSafeTimedSerializer; keys list = `[*SECRET_KEY_FALLBACKS, secret_key]` (current key LAST/top for signing); salt "cookie-session"; lazy sha1 digest (FIPS-safe).

### Decisive source
```python
# open:
if s is None: return None                 # no secret key → null-session path
val = request.cookies.get(self.get_cookie_name(app))
if not val: return self.session_class()
try:
    data = s.loads(val, max_age=int(app.permanent_session_lifetime.total_seconds()))
    return self.session_class(data)
except BadSignature:
    return self.session_class()           # tampered/expired ⇒ FRESH empty session

# save:
if session.accessed: response.vary.add("Cookie")
if not session:
    if session.modified:
        response.delete_cookie(...); response.vary.add("Cookie")
    return                                # empty+unmodified ⇒ no cookie work
if not self.should_set_cookie(app, session): return   # modified OR permanent&&refresh
val = self.get_signing_serializer(app).dumps(dict(session))
response.set_cookie(name, val, expires=..., httponly=..., domain=..., path=...,
                    secure=..., partitioned=..., samesite=...)
response.vary.add("Cookie")
```

**Flow:** push-time open (lazy, in ctx) → BadSignature silently yields fresh session → process_response save: accessed⇒Vary; modified-empty⇒delete; should_set_cookie gate; dump whole dict.
**Invariant:** `modified` is CallbackDict-tracked — mutations of NESTED mutables do NOT flip it (must set manually); `accessed` is set by the context's session property and drives Vary even without modification; fallback keys let old cookies keep validating across rotation but are never used to SIGN.
**Probe:** `grep -Fc '# itsdangerous expects current key at top' src/flask/sessions.py` = 1; `grep -Fc 'except BadSignature:' src/flask/sessions.py` = 1; `grep -Fc 'response.delete_cookie(' src/flask/sessions.py` = 1; tests `tests/test_basic.py::test_session_secret_key_fallbacks` (:396), `::test_session_vary_cookie` (:542), `::test_session_special_types` (:470).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "SecureCookieSessionInterface save_session open_session signing serializer", limit: 8 });
```

## Verdict
Adopt the full decision tree incl. Vary bookkeeping. Adapt to server-side stores by keeping only the interface contract (`open_session` returning None ⇒ NullSession). Omit pickle_based flag legacy.
