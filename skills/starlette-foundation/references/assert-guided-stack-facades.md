<!-- capsule-v2 -->
# Assert-guided optional-stack facades — how should `request.session` fail when the middleware that feeds it isn't installed?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** What error should a connection property raise when its producing middleware is missing, and how does read-access tracking reach the session object without hard-coupling to it?

## session / auth / user properties
**Path/Symbol:** `starlette/requests.py:HTTPConnection.session` (:169-176), `.auth` (:178-181), `.user` (:183-186).
**Signature:** `@property def session(self) -> dict[str, Any]`; `@property def auth(self) -> Any` / `def user(self) -> Any`.
**Data Shape:** each reads one scope key injected by an optional middleware (`session` ← SessionMiddleware, `auth`/`user` ← AuthenticationMiddleware); absent key ⇒ AssertionError, never KeyError.

### Decisive source
```python
@property
def session(self) -> dict[str, Any]:
    assert "session" in self.scope, "SessionMiddleware must be installed to access request.session"
    session: Session = self.scope["session"]
    # We keep the hasattr in case people actually use their own `SessionMiddleware` implementation.
    if hasattr(session, "mark_accessed"):  # pragma: no branch
        session.mark_accessed()
    return session

@property
def auth(self) -> Any:
    assert "auth" in self.scope, "AuthenticationMiddleware must be installed to access request.auth"
    return self.scope["auth"]
```

**Flow:** endpoint touches `request.session` → assert checks the scope contract FIRST and names the missing middleware in the message → duck-typed access-tracking hook fires only if the object offers `mark_accessed()` → value returned. The hook is what drives SessionMiddleware's `Vary: Cookie` emission (middleware side covered in session-signed-cookies); the request side deliberately does NOT import or isinstance-check the Session class.
**Invariant:** misconfiguration surfaces as an actionable AssertionError at point of use — not as a KeyError from deep inside user code. Third-party session implementations work because coupling is structural (hasattr), not nominal.
**Probe:** coverage caveat: no direct test pins these assert messages or mark_accessed at this pin; the hook's effect is pinned indirectly by `tests/middleware/test_session.py::test_vary_cookie_on_access` (:227, cited in session-signed-cookies).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", filePattern: "*requests*", namePattern: "^(session|auth|user)$", limit: 10 });
```

## Verdict
Adopt assert-with-middleware-name for every optional-stack facade property — the error message is documentation that fires exactly when needed. Adapt to your language's failure idiom (raise a config-specific exception instead of assert if asserts may be compiled out). Omit the duck-typed hook only if you own both sides nominally; otherwise keep coupling hasattr-thin so drop-in replacements keep working.
