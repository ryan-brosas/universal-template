<!-- capsule-v2 -->
# Admin Gate Dual-Credential — operator session OR bearer token, never a third answer

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** How does one dependency accept both dashboard operators and CI automation without weakening either path?

## token-first short-circuit; 403 (not 503) when unauthenticated
**Path/Symbol:** `packages/python/awaithumans/server/core/admin_auth.py` — docstring (:1-12), `_has_valid_admin_token` (:27-39), `_is_operator_session` (:42-44), `require_admin` (:47-55).
**Signature:** `async require_admin(request: Request) -> None` — FastAPI dependency, raises HTTPException(403) or returns.
**Data Shape:** credential A = `X-Admin-Token: <token>` header (or `Authorization: Bearer <ADMIN_API_TOKEN>` pre-detected by the dashboard middleware into `request.state.auth_admin_token`); credential B = operator session claims (`request.state.auth_claims` is `SessionClaims` with `is_operator=True`).

### Decisive source
```python
def _has_valid_admin_token(request, header_value):
    if getattr(request.state, "auth_admin_token", False):   # middleware already matched Bearer
        return True
    if not settings.ADMIN_API_TOKEN:
        return False                                        # unset token ⇒ that path closed
    return hmac.compare_digest(header_value, settings.ADMIN_API_TOKEN)
...
raise HTTPException(status_code=403, detail="Admin access required.")
```
Docstring: 403 not 503 because "operators can still reach it via the dashboard login" — the resource exists and is forbidden, not unavailable.

**Flow:** route declares `dependencies=[Depends(require_admin)]` → admin-token check first (constant-time compare; header form compared directly, bearer form trusted from middleware state) → operator-session check → 403. Unset ADMIN_API_TOKEN disables only the token path; missing/invalid session claims close only the session path.
**Invariant:** comparison is constant-time (timing-leak defense); the two credentials are independent — neither can impersonate the other, and absence of both is the ONLY failure.
**Probe:** `packages/python/tests/users/test_admin_routes.py` (`test_list_requires_admin_token`:69 — no session+no token ⇒ 401 at the middleware boundary, `test_wrong_token_rejected`:77) + every route in `routes/slack/installations.py` is gated by this dependency (:38).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "require_admin _has_valid_admin_token _is_operator_session", limit: 4 });
```
Live rank-1..4 line-exact (note rank-3 is core/auth.py's own twin helper — same name, different module; route by file).

## Verdict
Adopt the dual-credential dependency shape with constant-time compares; adapt claim type/token env to your auth stack; omit the middleware-precomputed-bearer flag only if your middleware doesn't already consume bearer tokens (then compare the header yourself).
